import asyncio
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_runtime import ScriptedModel
from app import (JsonlTrace, MAX_OUTPUT_BYTES, WorkspaceTools, call, coding_run,
                 execute_process, fixture_model, prepare_demo, summarize_trace, main_async)


class CodingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.events = []

    async def test_real_repair_loop_and_trace_without_api(self):
        prepare_demo(self.root)
        trace_path = self.root / "trace.jsonl"
        trace = JsonlTrace(trace_path, "fixture")
        workspace = WorkspaceTools(self.root, lambda action: True, trace)
        try:
            model = fixture_model()
            result = await coding_run(model, workspace, "Fix add", trace)
        finally:
            trace.close()
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.turns, 6)
        self.assertEqual(result.tool_calls, 5)
        self.assertEqual([r["returncode"] for r in workspace.commands], [1, 0])
        self.assertIn("FAILED (failures=1)", workspace.commands[0]["stderr"])
        self.assertIn("OK", workspace.commands[1]["stderr"])
        self.assertEqual((self.root / "calculator.py").read_text(), "def add(a, b):\n    return a + b\n")
        # Verify actual tool results reached the following model request.
        tool_messages = [m for m in model.requests[-1]["messages"] if m["role"] == "tool"]
        self.assertEqual(json.loads(tool_messages[-1]["content"])["result"]["returncode"], 0)
        records = [json.loads(line) for line in trace_path.read_text().splitlines()]
        self.assertEqual(records[-1]["status"], "complete")
        self.assertEqual([r["returncode"] for r in records if r["event"] == "process.end"], [1, 0])
        measured = summarize_trace(trace_path)
        self.assertEqual(measured["commands"], 2)
        self.assertEqual(measured["nonzero_commands"], 1)
        self.assertEqual(measured["tool_dispatch_failures"], 0)
        self.assertEqual(measured["writes"], 1)
        self.assertEqual(measured["runtime_statuses"], ["complete"])
        serialized = trace_path.read_text()
        self.assertNotIn("return a + b", serialized)
        self.assertNotIn("arguments", serialized)
        self.assertNotIn("Fix add", serialized)

    async def test_denial_starts_no_process_and_does_not_edit(self):
        prepare_demo(self.root)
        workspace = WorkspaceTools(self.root, lambda action: False, self.events.append)
        original = (self.root / "calculator.py").read_text()
        model = ScriptedModel([
            call("run_command", {"argv": [sys.executable, "-c", "raise RuntimeError('must not run')"]}, "denied"),
            call("read_file", {"path": "calculator.py"}, "read"),
            call("write_file", {"path": "calculator.py", "content": "changed"}, "write"),
            {"role": "assistant", "content": "Operation denied."},
        ])
        result = await coding_run(model, workspace, "Denied operations", self.events.append)
        self.assertEqual(result.status, "complete")
        results = [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]
        self.assertFalse(results[0]["ok"])
        self.assertFalse(results[2]["ok"])
        self.assertEqual(workspace.commands, [])
        self.assertFalse(any(e["event"] == "process.start" for e in self.events))
        self.assertEqual((self.root / "calculator.py").read_text(), original)

    async def test_workspace_boundaries_and_read_before_write(self):
        workspace = WorkspaceTools(self.root, lambda _: True)
        target = self.root / "existing.txt"
        target.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            await workspace.write_file("existing.txt", "replace")
        for invalid in ("../outside.txt", "/tmp/outside.txt", "..\\outside.txt"):
            with self.assertRaises(ValueError):
                workspace.read_file(invalid)
            with self.assertRaises(ValueError):
                await workspace.write_file(invalid, "bad")
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "secret.txt"
            outside.write_text("private")
            (self.root / "link").symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                workspace.read_file("link/secret.txt")
            with self.assertRaises(ValueError):
                await workspace.write_file("link/secret.txt", "overwrite")
            self.assertEqual(outside.read_text(), "private")
        workspace.read_file("existing.txt")
        await workspace.write_file("existing.txt", "新内容")
        self.assertEqual(target.read_text(), "新内容")
        self.assertEqual(list(self.root.glob(".agent-write-*")), [])

    async def test_write_approval_shows_diff_and_preserves_intervening_edit(self):
        file = self.root / "sample.txt"
        file.write_text("old\n")
        seen = []
        def approve(action):
            seen.append(action)
            file.write_text("user edit\n")
            return True
        workspace = WorkspaceTools(self.root, approve)
        workspace.read_file("sample.txt")
        with self.assertRaisesRegex(ValueError, "changed while awaiting approval"):
            await workspace.write_file("sample.txt", "replacement\n")
        self.assertIn("-old", seen[0]["diff"])
        self.assertIn("+replacement", seen[0]["diff"])
        self.assertEqual(file.read_text(), "user edit\n")

    async def test_timeout_retains_output_and_reaps_process(self):
        events = []
        result = await execute_process([sys.executable, "-u", "-c",
            "import time; print('started'); time.sleep(20)"], self.root, .15, events.append)
        self.assertTrue(result["timed_out"])
        self.assertIn("started", result["stdout"])
        self.assertIsNotNone(result["returncode"])
        self.assertTrue(events[-1]["timed_out"])

    async def test_entrypoint_cancellation_closes_model_client(self):
        started = asyncio.Event()
        class ClientFixture:
            closed = False
            async def complete(self, messages, tools):
                started.set()
                await asyncio.sleep(60)
            async def aclose(self):
                self.closed = True
        client = ClientFixture()
        args = argparse.Namespace(live=True, workspace=str(self.root), task="lifecycle test",
                                  trace=str(self.root / "lifecycle.jsonl"), command_timeout=1,
                                  scenario="repair")
        # A test provider is injected; this is not a live API request.
        with patch("app.model_from_env", return_value=client):
            task = asyncio.create_task(main_async(args))
            await asyncio.wait_for(started.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(client.closed)
        rows = [json.loads(row) for row in (self.root / "lifecycle.jsonl").read_text().splitlines()]
        self.assertEqual(rows[-1]["status"], "cancelled")

    async def test_cancellation_reaps_process_and_surfaces_cancel(self):
        started = asyncio.Event()
        events = []
        def emit(event):
            events.append(event)
            if event["event"] == "process.start":
                started.set()
        task = asyncio.create_task(execute_process(
            [sys.executable, "-c", "import time; time.sleep(20)"], self.root, 30, emit))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(events[-1]["cancelled"])
        self.assertIsNotNone(events[-1]["returncode"])
        if os.name == "posix":
            with self.assertRaises(ProcessLookupError):
                os.kill(events[0]["pid"], 0)

    async def test_output_bound_and_nonzero_exit_are_actual_results(self):
        result = await execute_process([sys.executable, "-c",
            "import sys; print('x'*10000); print('bad', file=sys.stderr); sys.exit(7)"],
            self.root, 2, self.events.append)
        self.assertEqual(result["returncode"], 7)
        self.assertTrue(result["truncated"])
        self.assertGreater(result["stdout_bytes"], MAX_OUTPUT_BYTES)
        self.assertEqual(len(result["stdout"].encode()), MAX_OUTPUT_BYTES)
        self.assertEqual(result["stderr"], "bad\n")

    async def test_runtime_schema_error_and_exhausted_fixture_are_visible(self):
        workspace = WorkspaceTools(self.root, lambda _: True)
        model = ScriptedModel([call("read_file", {"path": "ok", "surprise": True}, "invalid")])
        result = await coding_run(model, workspace, "Invalid schema")
        self.assertEqual(result.status, "error")
        message = next(m for m in result.messages if m["role"] == "tool")
        self.assertEqual(json.loads(message["content"])["error_type"], "ValidationError")


class EntrypointTests(unittest.TestCase):
    def test_live_without_credentials_has_no_fixture_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            env.pop("OPENAI_MODEL", None)
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("app.py")),
                                    "--live", "--workspace", directory], env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("OPENAI_API_KEY", result.stderr)
            self.assertNotIn("MODE fixture", result.stdout)

    def test_default_cli_is_offline_and_does_not_write_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "run.jsonl"
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("app.py")),
                "--trace", str(trace)], cwd=directory, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("MODE fixture", result.stdout)
            self.assertIn("COMMAND 1: exit=1", result.stdout)
            self.assertIn("COMMAND 2: exit=0", result.stdout)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["run.jsonl"])


if __name__ == "__main__":
    unittest.main()
