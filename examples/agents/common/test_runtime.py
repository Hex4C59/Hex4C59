import asyncio
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import tempfile
import unittest

from agent_runtime import (Tool, ScriptedModel, run_agent, confined_path,
                           atomic_write_text, model_from_env, OpenAIChatModel)
from unittest.mock import patch


def request(name, arguments, identity="call_1"):
    return {"role": "assistant", "content": None, "tool_calls": [{
        "id": identity, "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]}


SCHEMA = {"type": "object", "properties": {"value": {"type": "integer"}},
          "required": ["value"], "additionalProperties": False}


class LoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_tools_execute_in_order_and_feedback_is_sent(self):
        values, events = [], []
        tool = Tool("remember", "Append a number", SCHEMA,
                    lambda value: values.append(value) or len(values))
        first = request("remember", {"value": 3})
        second = request("remember", {"value": 4}, "call_2")
        first["tool_calls"].extend(second["tool_calls"])
        model = ScriptedModel([first, {"role": "assistant", "content": "saved"}])
        result = await run_agent(model, "Use tools", "save", [tool], on_event=events.append)
        self.assertEqual((result.status, result.text, result.tool_calls), ("complete", "saved", 2))
        self.assertEqual(values, [3, 4])
        feedback = model.requests[1]["messages"][-2:]
        self.assertEqual([m["tool_call_id"] for m in feedback], ["call_1", "call_2"])
        self.assertEqual([json.loads(m["content"])["result"] for m in feedback], [1, 2])
        self.assertEqual(events[-1]["status"], "complete")
        self.assertFalse(any("content" in event or "arguments" in event for event in events))

    async def test_invalid_arguments_and_unknown_tools_do_not_execute(self):
        effects = []
        tool = Tool("act", "Record", SCHEMA, lambda **args: effects.append(args))
        for name, arguments in [("absent", {}), ("act", {"value": "wrong"}),
                                ("act", {"value": 1, "extra": True})]:
            with self.subTest(name=name, arguments=arguments):
                model = ScriptedModel([request(name, arguments), {"content": "cannot do that"}])
                result = await run_agent(model, "", "", [tool])
                self.assertEqual(result.status, "complete")
                self.assertFalse(json.loads(result.messages[-2]["content"])["ok"])
        self.assertEqual(effects, [])

    async def test_tool_error_is_visible_and_model_can_recover(self):
        def failing(value):
            raise OSError("synthetic I/O failure")
        model = ScriptedModel([request("act", {"value": 1}), {"content": "failed, no file saved"}])
        result = await run_agent(model, "", "", [Tool("act", "fail", SCHEMA, failing)])
        feedback = json.loads(result.messages[-2]["content"])
        self.assertFalse(feedback["ok"])
        self.assertEqual(feedback["error_type"], "OSError")

    async def test_async_handler_and_deadline(self):
        finished = []
        async def blocked(value):
            try:
                await asyncio.sleep(10)
                finished.append(value)
            finally:
                finished.append("cancelled")
        result = await run_agent(ScriptedModel([request("wait", {"value": 1})]), "", "",
                                 [Tool("wait", "wait", SCHEMA, blocked)], timeout=0.02)
        self.assertEqual(result.status, "timeout")
        self.assertEqual(finished, ["cancelled"])

    async def test_cancellation_is_propagated_and_reported(self):
        started = asyncio.Event()
        events = []
        class WaitingModel:
            async def complete(self, *_):
                started.set()
                await asyncio.sleep(10)
        task = asyncio.create_task(run_agent(WaitingModel(), "", "", [], on_event=events.append))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(events[-1]["status"], "cancelled")

    async def test_limits_and_fixture_exhaustion_are_not_success(self):
        tool = Tool("act", "record", SCHEMA, lambda value: value)
        first = request("act", {"value": 1})
        first["tool_calls"].extend(request("act", {"value": 2}, "call_2")["tool_calls"])
        model = ScriptedModel([first])
        result = await run_agent(model, "", "", [tool], max_tool_calls=1)
        self.assertEqual((result.status, result.tool_calls), ("limit", 1))
        result = await run_agent(ScriptedModel([request("act", {"value": 1})]), "", "", [tool], max_turns=1)
        self.assertEqual(result.status, "limit")
        result = await run_agent(ScriptedModel([]), "", "", [])
        self.assertEqual(result.status, "error")

    async def test_malformed_and_duplicate_call_ids_are_rejected(self):
        call = request("act", {"value": 1})
        call["tool_calls"] *= 2
        result = await run_agent(ScriptedModel([call]), "", "", [])
        self.assertEqual(result.status, "error")
        self.assertEqual(result.tool_calls, 0)

    async def test_oversized_and_non_json_results_return_errors(self):
        for value in ["x" * 32_001, float("nan"), object()]:
            model = ScriptedModel([request("act", {"value": 1}), {"content": "result unavailable"}])
            result = await run_agent(model, "", "", [Tool("act", "act", SCHEMA, lambda **_: value)])
            self.assertFalse(json.loads(result.messages[-2]["content"])["ok"])


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_installed_async_sdk_against_real_local_http_endpoint(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                captured.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                payload = json.dumps({"id": "fixture-http", "object": "chat.completion",
                    "created": 1, "model": "fixture-model", "choices": [{"index": 0,
                    "finish_reason": "tool_calls", "message": request("act", {"value": 7})}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = "http://127.0.0.1:%d/v1" % server.server_port
            async with OpenAIChatModel("local-fixture-key", "fixture-model", base_url) as model:
                result = await model.complete([{"role": "user", "content": "fixture request"}],
                    [Tool("act", "record", SCHEMA, lambda value: value).definition()])
            self.assertEqual(result["tool_calls"][0]["function"]["name"], "act")
            self.assertEqual(captured[0][0], "/v1/chat/completions")
            self.assertEqual(captured[0][1]["model"], "fixture-model")
            self.assertEqual(captured[0][1]["tools"][0]["function"]["name"], "act")
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(timeout=2)


class FileBoundaryTests(unittest.TestCase):
    def test_real_file_write_and_rejected_escape_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = confined_path(root, "answer.txt")
            atomic_write_text(target, "first")
            atomic_write_text(target, "second")
            self.assertEqual(target.read_text(), "second")
            self.assertEqual(list(root.glob('.agent-write-*')), [])
            for name in ["../outside", "/tmp/outside", "", "a/../../outside", "a\\b"]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    confined_path(root, name)
            self.assertEqual(confined_path(root, ".", allow_root=True), root.resolve())

    def test_symlink_targets_and_components_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "link").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                confined_path(root, "link/stolen.txt")
            (root / "target").write_text("original")
            (root / "alias").symlink_to(root / "target")
            with self.assertRaises(ValueError):
                atomic_write_text(root / "alias", "replacement")
            self.assertEqual((root / "target").read_text(), "original")

    def test_live_mode_fails_without_keys_before_network(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(ValueError):
            model_from_env()


if __name__ == "__main__":
    unittest.main()
