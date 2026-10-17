"""Offline tests: SQLite, actual child processes and the shared validated loop."""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import app
from agent_runtime import ScriptedModel


def tool_payloads(result):
    return [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="memory-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = app.MemoryStore(self.root / "state")

    def cli(self, *args):
        return subprocess.run([sys.executable, str(Path(app.__file__).resolve()), *args,
                               "--workspace", str(self.root), "--user", "sample-a",
                               "--session", "session-a"], capture_output=True, text=True, timeout=10)

    def test_real_process_restart_and_user_isolation(self):
        written = self.cli("put", "--key", "style", "--value", "synthetic concise", "--confirm")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.store.put("sample-b", "session-b", "preference", "style", "synthetic detailed")
        restarted = self.cli("get", "--key", "style")
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        self.assertEqual(json.loads(restarted.stdout)["record"]["value"], "synthetic concise")
        self.assertEqual(self.store.search("sample-b", "synthetic")[0]["value"], "synthetic detailed")
        self.assertNotIn("detailed", restarted.stdout)
        self.assertEqual(app.MemoryStore(self.root / "state").get("sample-a", "preference", "style")["revision"], 1)

    def test_crud_revision_kind_and_delete_are_scoped(self):
        self.store.put("a", "one", "preference", "style", "old")
        self.store.put("b", "one", "preference", "style", "other user")
        self.store.put("a", "one", "episode", "style", "event")
        updated = self.store.put("a", "two", "preference", "style", "new")
        self.assertEqual((updated["revision"], updated["source_session"]), (2, "two"))
        self.assertTrue(self.store.delete("a", "preference", "style"))
        self.assertFalse(self.store.delete("a", "preference", "style"))
        self.assertIsNone(self.store.get("a", "preference", "style"))
        self.assertEqual(self.store.get("b", "preference", "style")["value"], "other user")
        self.assertEqual(self.store.get("a", "episode", "style")["value"], "event")

    def test_quota_and_oversize_update_roll_back(self):
        for i in range(app.MAX_PER_USER):
            self.store.put("a", "s", "preference", f"key{i}", "kept")
        with self.assertRaises(app.StoreError):
            self.store.put("a", "s", "preference", "extra", "not saved")
        with self.assertRaises(app.StoreError):
            self.store.put("a", "s", "preference", "key0", "x" * (app.MAX_VALUE + 1))
        self.assertEqual(self.store.get("a", "preference", "key0")["value"], "kept")
        self.assertEqual(self.store.put("a", "s", "preference", "key0", "updated")["revision"], 2)
        with patch.object(app, "MAX_RECORDS", app.MAX_PER_USER):
            with self.assertRaises(app.StoreError):
                self.store.put("b", "s", "preference", "global_limit", "not saved")
        self.assertIsNone(self.store.get("b", "preference", "global_limit"))

    def test_search_is_bounded_literal_and_parameterized(self):
        self.store.put("a", "s", "episode", "one", "100%_quote' 中文记录")
        self.store.put("a", "s", "episode", "two", "normal")
        self.assertEqual(len(self.store.search("a", "%_")), 1)
        self.assertEqual(len(self.store.search("a", "中文")), 1)
        self.assertEqual(self.store.search("a", "' OR 1=1 --"), [])
        for limit in (0, 11, True, "1"):
            with self.subTest(limit=limit), self.assertRaises(app.StoreError):
                self.store.search("a", "", limit)
        for value in ("", " ", "x" * 513, "a\0b", None):
            with self.subTest(value=repr(value)), self.assertRaises(app.StoreError):
                self.store.put("a", "s", "preference", "invalid", value)
        with self.assertRaises(app.StoreError):
            self.store.get("../other", "preference", "one")

    def test_locked_writer_fails_without_losing_old_value(self):
        self.store.put("a", "s", "preference", "style", "old")
        connection = sqlite3.connect(self.store.path, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            with self.assertRaises(app.StoreError):
                self.store.put("a", "s", "preference", "style", "uncommitted")
        finally:
            connection.rollback()
            connection.close()
        self.assertEqual(self.store.get("a", "preference", "style")["value"], "old")

    def test_corrupt_unknown_and_malformed_stores_are_not_reset(self):
        corrupt = self.root / "corrupt"
        corrupt.mkdir()
        db_path = corrupt / "memory.sqlite3"
        db_path.write_bytes(b"not a SQLite database")
        before = db_path.read_bytes()
        with self.assertRaises(app.StoreError):
            app.MemoryStore(corrupt)
        self.assertEqual(db_path.read_bytes(), before)
        for version in (0, 99, 1):
            with self.subTest(version=version):
                directory = self.root / f"bad-{version}"
                directory.mkdir()
                connection = sqlite3.connect(directory / "memory.sqlite3")
                connection.execute("CREATE TABLE unrelated (value TEXT)")
                connection.execute(f"PRAGMA user_version={version}")
                connection.commit(); connection.close()
                with self.assertRaises(app.StoreError):
                    app.MemoryStore(directory)
                connection = sqlite3.connect(directory / "memory.sqlite3")
                self.assertEqual(connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [("unrelated",)])
                connection.close()
        directory = self.root / "malformed"
        directory.mkdir()
        connection = sqlite3.connect(directory / "memory.sqlite3")
        connection.execute("CREATE TABLE memory (wrong_column TEXT)")
        connection.execute("PRAGMA user_version=1")
        connection.close()
        with self.assertRaises(app.StoreError):
            app.MemoryStore(directory)

    def test_concurrent_process_updates_do_not_lose_revisions(self):
        self.store.put("a", "s", "preference", "counter", "start")
        code = ("import sys; from pathlib import Path; from app import MemoryStore; "
                "s=MemoryStore(Path(sys.argv[1])); "
                "[s.put('a','child','preference','counter',str(i)) for i in range(12)]")
        children = [subprocess.Popen([sys.executable, "-c", code, str(self.root / "state")],
                                    cwd=Path(app.__file__).resolve().parent,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = []
        try:
            for child in children:
                stdout, stderr = child.communicate(timeout=10)
                results.append((child.returncode, stdout, stderr))
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill(); child.wait()
                if child.stdout is not None:
                    child.stdout.close()
                if child.stderr is not None:
                    child.stderr.close()
        for code, stdout, stderr in results:
            self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(self.store.get("a", "preference", "counter")["revision"], 25)

    def test_cli_requires_scope_and_mutation_confirmation(self):
        no_confirm = self.cli("put", "--key", "style", "--value", "not approved")
        self.assertEqual(no_confirm.returncode, 2)
        self.assertIn("--confirm", no_confirm.stderr)
        self.assertIsNone(self.store.get("sample-a", "preference", "style"))
        missing = subprocess.run([sys.executable, str(Path(app.__file__).resolve()), "get", "--key", "style"],
                                 capture_output=True, text=True, timeout=5)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--user", missing.stderr)
        partial = subprocess.run([sys.executable, str(Path(app.__file__).resolve()),
                                  "--user", "sample-a", "--session", "s"],
                                 capture_output=True, text=True, timeout=5)
        self.assertEqual(partial.returncode, 2)
        self.assertIn("--workspace", partial.stderr)

    def test_default_demo_uses_real_processes_and_keeps_entrypoint(self):
        source = Path(app.__file__).resolve()
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        run = subprocess.run([sys.executable, str(source)], capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("fixture restart: user=demo-alice session=session-2", run.stdout)
        self.assertIn("other user's preference absent", run.stdout)
        self.assertIn('demo_application/main.py: {"status": "ok"}', run.stdout)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


class AgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="memory-agent-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = app.MemoryStore(self.root / "state")

    def agent(self, responses, **kwargs):
        scripted = ScriptedModel(responses)
        return app.MemoryAgent(self.store, self.root, "a", "session-a", scripted, **kwargs), scripted

    async def test_unapproved_put_and_self_claimed_confirmation_cannot_save(self):
        responses = [app.call("memory_put", {"kind": "preference", "key": "style", "value": "secretly saved"}),
                     app.call("memory_put", {"kind": "preference", "key": "style", "value": "self approved", "confirmed": True}, 2),
                     app.final("fixture")]
        agent, _ = self.agent(responses)
        result = await agent.ask("仅讨论一项假设偏好，不同意保存。")
        payloads = tool_payloads(result)
        self.assertEqual(result.status, "complete")
        self.assertTrue(all(not item["ok"] for item in payloads))
        self.assertEqual(payloads[0]["error_type"], "PermissionError")
        self.assertIsNone(self.store.get("a", "preference", "style"))

    async def test_approval_matches_exact_value_and_is_consumed_after_commit(self):
        def put(value, number):
            return app.call("memory_put", {"kind": "preference", "key": "style", "value": value}, number)
        agent, _ = self.agent([put("wrong", 1), put("confirmed", 2), put("confirmed", 3), app.final("fixture")],
                              approvals=app.Approvals({("preference", "style", "confirmed")}))
        result = await agent.ask("保存命令行已经确认的具体值。")
        self.assertEqual([p["ok"] for p in tool_payloads(result)], [False, True, False])
        self.assertEqual(self.store.get("a", "preference", "style")["revision"], 1)

    async def test_restart_retrieval_is_user_scoped_and_not_a_system_instruction(self):
        self.store.put("a", "old-session", "preference", "style", "synthetic concise")
        self.store.put("b", "other-session", "preference", "style", "synthetic other user")
        agent, scripted = self.agent([app.final("fixture")])
        await agent.ask("沿用我的风格。")
        request = scripted.requests[0]
        envelope = json.loads(request["messages"][1]["content"])
        self.assertEqual(envelope["retrieved_memory"][0]["source_session"], "old-session")
        self.assertEqual(request["messages"][1]["role"], "user")
        self.assertNotIn("synthetic other user", app.packed(request))
        self.assertNotIn("synthetic concise", request["messages"][0]["content"])

    async def test_tool_args_reject_wrong_scope_types_lengths_json_and_traversal(self):
        invalid = [
            ("memory_get", '{"kind":"preference","key":"style","user_id":"b"}'),
            ("memory_get", "not-json"),
            ("memory_get", "[]"),
            ("memory_search", '{"query":"","limit":true}'),
            ("memory_search", '{"query":"","limit":11}'),
            ("memory_put", app.packed({"kind": "preference", "key": "style", "value": "x" * 513})),
            ("write_demo_file", '{"path":"../app.py","content":"bad"}'),
        ]
        sentinel = self.root / "app.py"
        sentinel.write_text("keep", encoding="utf-8")
        for name, raw in invalid:
            with self.subTest(tool=name, raw=raw[:50]):
                response = app.call(name, {})
                response["tool_calls"][0]["function"]["arguments"] = raw
                agent, _ = self.agent([response, app.final("fixture error handled")])
                result = await agent.ask("检查错误参数。")
                self.assertEqual(result.status, "complete")
                self.assertFalse(tool_payloads(result)[0]["ok"])
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(self.store.search("a"), [])
        # Even an explicitly selected workspace cannot make the file tool replace its entrypoint.
        nested_entry = self.root / "demo_application" / "app.py"
        nested_entry.write_text("keep entrypoint", encoding="utf-8")
        agent, _ = self.agent([app.call("write_demo_file", {"path": "app.py", "content": "bad"}),
                               app.final("fixture rejected")])
        with patch.object(app, "__file__", str(nested_entry)):
            result = await agent.ask("检查入口保护。")
        self.assertFalse(tool_payloads(result)[0]["ok"])
        self.assertEqual(nested_entry.read_text(), "keep entrypoint")

    async def test_confirmed_delete_clears_history_without_exit_resurrection(self):
        self.store.put("a", "old", "preference", "style", "old preference")
        agent, scripted = self.agent([app.call("memory_delete", {"kind": "preference", "key": "style"}),
                                      app.final("fixture deleted"), app.final("fixture next")],
                                     approvals=app.Approvals(deletes={("preference", "style")}))
        agent.history.append("old preference", "not new consent")
        result = await agent.ask("删除已经确认的这项记忆。")
        self.assertTrue(tool_payloads(result)[0]["result"]["deleted"])
        self.assertEqual(agent.history.pairs, [])
        await agent.ask("新会话输入。")
        self.assertIsNone(self.store.get("a", "preference", "style"))
        last = json.loads(scripted.requests[-1]["messages"][1]["content"])
        self.assertEqual(last["retrieved_memory"], [])
        self.assertEqual(last["session_history"], [])

    async def test_history_and_retrieved_context_are_actually_bounded(self):
        for i in range(10):
            self.store.put("a", "s", "preference", f"pref{i}", "假设数据" * 100)
        agent, scripted = self.agent([app.final("固定回答" * 400) for _ in range(18)])
        for number in range(18):
            result = await agent.ask(f"task-{number}:" + "x" * 900)
            self.assertEqual(result.status, "complete")
            self.assertLessEqual(len(app.packed(agent.history.pairs)), app.MAX_HISTORY_CHARS)
            self.assertLessEqual(len(agent.history.pairs), app.MAX_HISTORY_PAIRS)
        self.assertGreater(agent.history.dropped_pairs, 0)
        for request in scripted.requests:
            envelope = json.loads(request["messages"][1]["content"])
            self.assertLessEqual(len(app.packed(envelope["retrieved_memory"])), app.MAX_CONTEXT_CHARS)
            self.assertLessEqual(app.request_chars(**request), app.REQUEST_CHAR_BUDGET)
        self.assertNotIn("task-0:", app.packed(scripted.requests[-1]))

    async def test_compaction_preserves_complete_tool_exchanges_before_every_call(self):
        for i in range(10):
            self.store.put("a", "s", "episode", f"event{i}", "x" * 512)
        responses = [app.call("memory_search", {"query": "", "limit": 10}, i) for i in range(6)]
        agent, scripted = self.agent(responses + [app.final("fixture done")])
        result = await agent.ask("检索历史事件。")
        self.assertEqual(result.status, "complete")
        self.assertGreater(agent.model.compactions, 0)
        self.assertEqual(len(agent.model.measurements), 7)
        for request, measured in zip(scripted.requests, agent.model.measurements):
            self.assertEqual(measured, app.request_chars(**request))
            self.assertLessEqual(measured, app.REQUEST_CHAR_BUDGET)
            pending = set()
            for message in request["messages"]:
                if message["role"] == "assistant":
                    self.assertFalse(pending)
                    pending = {call["id"] for call in message.get("tool_calls", [])}
                elif message["role"] == "tool":
                    self.assertIn(message["tool_call_id"], pending)
                    pending.remove(message["tool_call_id"])
            self.assertFalse(pending)

    async def test_unshrinkable_request_rejected_before_underlying_model_call(self):
        agent, scripted = self.agent([app.final("must not run")], budget=1)
        result = await agent.ask("valid task")
        self.assertEqual(result.status, "error")
        self.assertEqual(scripted.requests, [])
        self.assertEqual(agent.model.measurements, [])

    async def test_cancelled_model_does_not_save_or_append_history(self):
        started = asyncio.Event()
        class Blocking:
            async def complete(self, messages, tools):
                started.set()
                await asyncio.Event().wait()
        agent = app.MemoryAgent(self.store, self.root, "a", "s", Blocking())
        task = asyncio.create_task(agent.ask("不要自动保存这段讨论。"))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.store.search("a"), [])
        self.assertEqual(agent.history.pairs, [])

    async def test_live_adapter_is_closed_even_on_model_failure(self):
        class FakeAsyncClient:
            closed = False
            async def complete(self, messages, tools):
                raise RuntimeError("synthetic provider failure")
            async def aclose(self):
                self.closed = True
        model = FakeAsyncClient()
        args = app.parser().parse_args(["chat", "--live", "--workspace", str(self.root),
                                       "--user", "a", "--session", "s"])
        with patch.object(app, "model_from_env", return_value=model), contextlib.redirect_stdout(io.StringIO()):
            code = await app.selected_command(args)
        self.assertEqual(code, 1)
        self.assertTrue(model.closed)


if __name__ == "__main__":
    unittest.main()
