"""Real SDK subprocess integration tests; the model alone is a fixed fixture."""
import asyncio
import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path


async def sdk_test_server(mode, probe_dir):
    """Deliberately unusual but real protocol peers for error/content tests."""
    from mcp import types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from mcp.shared.exceptions import McpError

    Path(probe_dir, mode + ".pid").write_text(str(os.getpid()), encoding="utf-8")
    if mode == "hang":
        await asyncio.Event().wait()
    server = Server("test-peer")

    @server.list_tools()
    async def list_tools(request: types.ListToolsRequest):
        if mode == "list_error":
            raise McpError(types.ErrorData(code=-32602, message="synthetic list rejection"))
        if mode in ("paginated", "repeat_cursor"):
            cursor = request.params.cursor if request.params else None
            names = ["inspect_a"] if cursor is None else (["inspect_b"] if mode == "paginated" else [])
            return types.ListToolsResult(
                tools=[types.Tool(name=name, inputSchema={"type": "object", "properties": {},
                                                         "additionalProperties": False}) for name in names],
                nextCursor="next" if cursor is None or mode == "repeat_cursor" else None)
        if mode in ("remote_ref", "output_ref"):
            unsafe = {"type": "object", "properties": {"value": {"$ref": "https://example.invalid/schema"}}}
            if mode == "remote_ref":
                return [types.Tool(name="unsafe", inputSchema=unsafe)]
            return [types.Tool(name="unsafe", inputSchema={"type": "object", "properties": {}},
                               outputSchema=unsafe)]
        return [types.Tool(name="inspect", description="Synthetic protocol test",
                           inputSchema={"type": "object", "properties": {}, "additionalProperties": False})]

    # Use the low-level SDK request handler to return a JSON-RPC error instead of
    # FastMCP's tool-level isError. Transport/framing still belongs to the SDK.
    async def call_handler(request):
        if mode == "rpc_error":
            raise McpError(types.ErrorData(code=-32602, message="synthetic call rejection"))
        return types.ServerResult(types.CallToolResult(
            content=[types.TextContent(type="text", text="synthetic mixed content"),
                     types.ImageContent(type="image", data="AA==", mimeType="image/png")],
            structuredContent={"count": 1}, isError=False))

    server.request_handlers[types.CallToolRequest] = call_handler
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


# Run the protocol peer without importing the host/shared runtime. The server
# subprocess does not need PYTHONPATH or API credentials from its parent.
if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--sdk-server":
    asyncio.run(sdk_test_server(sys.argv[2], sys.argv[3]))
    raise SystemExit(0)

from jsonschema import ValidationError
from agent_runtime import ScriptedModel, run_agent
from app import HERE, SYSTEM, TASK, fixture_model
from connector import ConfigError, MCPToolError, connect_servers, load_config


def tool_response(name, args, call_id="test-call"):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {
            "name": name, "arguments": json.dumps(args)}}]}


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def exception_leaves(exc):
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for nested in exc.exceptions for leaf in exception_leaves(nested)]
    return [exc]


class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mcp-test-")
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.probes = self.root / "probes"
        self.workspace.mkdir()
        self.probes.mkdir()
        (self.workspace / "note.txt").write_text("synthetic MCP note\n", encoding="utf-8")
        self.base = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

    def config(self, *, two=False, peer=None, timeout=5.0):
        servers = self.base["servers"]
        if not two:
            servers.pop("mirror", None)
        for entry in servers.values():
            entry["cwd"] = str(HERE)
            entry["args"] += ["--probe-dir", str(self.probes)]
            entry["timeout_seconds"] = timeout
        if peer:
            servers["peer"] = {"command": "$PYTHON", "cwd": str(HERE),
                               "args": ["test_app.py", "--sdk-server", peer, str(self.probes)],
                               "timeout_seconds": timeout}
        target = self.root / "config.json"
        target.write_text(json.dumps(self.base), encoding="utf-8")
        return load_config(target, self.workspace)

    def pids(self):
        return [int(p.read_text()) for p in self.probes.glob("*.pid")]

    async def assert_reaped(self, expected=None):
        if os.name != "posix":
            return  # PID-zero inspection below is POSIX-only, not Windows evidence.
        if expected is not None:
            self.assertEqual(len(self.pids()), expected)
        for _ in range(100):
            if not any(alive(pid) for pid in self.pids()):
                return
            await asyncio.sleep(0.02)
        self.fail("An owned MCP server is still alive after context exit")

    async def asyncTearDown(self):
        try:
            await self.assert_reaped()
        finally:
            # Only PIDs recorded by servers launched in this test's private temp
            # directory are eligible for emergency cleanup after a failed test.
            if os.name == "posix":
                for pid in self.pids():
                    if alive(pid):
                        os.kill(pid, signal.SIGKILL)
            self.temp.cleanup()

    async def test_fixture_drives_two_real_servers_and_namespaced_tools(self):
        configs = self.config(two=True)
        model = fixture_model()
        async with connect_servers(configs) as manager:
            tools = manager.tools()
            self.assertEqual([t.name for t in tools], ["local__read_note", "mirror__read_note"])
            result = await run_agent(model, SYSTEM, TASK, tools)
            self.assertEqual(result.status, "complete")
            messages = [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]
            self.assertEqual(len(messages), 2)
            self.assertTrue(all(m["ok"] for m in messages))
            self.assertEqual([m["result"]["structured_content"]["label"] for m in messages], ["local", "mirror"])
            self.assertTrue(all(m["result"]["structured_content"]["text"] == "synthetic MCP note\n" for m in messages))
            self.assertEqual(len([e for e in manager.events if e["event"] == "initialize"]), 2)
            self.assertEqual([e["tool"] for e in manager.events if e["event"] == "call.ok"], ["read_note", "read_note"])
            self.assertEqual(model.requests[0]["tools"][0]["function"]["name"], "local__read_note")
            if os.name == "posix":
                self.assertTrue(all(alive(pid) for pid in self.pids()))
        self.assertTrue(manager.closed)
        with self.assertRaises(MCPToolError):
            manager.tools()
        await self.assert_reaped(2)

    async def test_server_is_error_reaches_model_and_can_recover(self):
        model = ScriptedModel([
            tool_response("local__read_note", {"path": "missing.txt"}, "missing"),
            tool_response("local__read_note", {"path": "note.txt"}, "recovery"),
            {"role": "assistant", "content": "fixture finished"}])
        async with connect_servers(self.config()) as manager:
            result = await run_agent(model, SYSTEM, TASK, manager.tools())
            payloads = [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]
            self.assertEqual(result.status, "complete")
            self.assertFalse(payloads[0]["ok"])
            self.assertIn("MCP tool:", payloads[0]["error"])
            self.assertTrue(payloads[1]["ok"])
            self.assertEqual([e.get("kind") for e in manager.events if e["event"] == "call.error"], ["tool"])
        await self.assert_reaped(1)

    async def test_real_server_rejects_traversal_absolute_symlink_and_large_file(self):
        outside = self.root / "private.txt"
        outside.write_text("must not be returned", encoding="utf-8")
        (self.workspace / "escape.txt").symlink_to(outside)
        (self.workspace / "large.txt").write_bytes(b"x" * 8193)
        async with connect_servers(self.config()) as manager:
            for requested in ("../private.txt", str(outside), "escape.txt", "large.txt"):
                with self.subTest(requested=requested):
                    with self.assertRaises(MCPToolError) as error:
                        await manager.call_tool("local__read_note", {"path": requested})
                    self.assertEqual(error.exception.kind, "tool")
                    self.assertNotIn("must not be returned", str(error.exception))
            with self.assertRaises(ValidationError):
                await manager.call_tool("local__read_note", {"path": "note.txt", "unexpected": True})
        await self.assert_reaped(1)

    async def test_partial_startup_failure_closes_previous_server(self):
        configs = self.config(two=True)
        from dataclasses import replace
        configs[1] = replace(configs[1], args=("-c", "raise SystemExit(7)"))
        with self.assertRaises(Exception):
            async with connect_servers(configs):
                self.fail("Second server should not initialize")
        await self.assert_reaped(1)

    async def test_discovery_failure_rolls_back_both_servers(self):
        with self.assertRaises(Exception) as error:
            async with connect_servers(self.config(peer="list_error")):
                self.fail("Discovery should fail")
        from mcp.shared.exceptions import McpError

        self.assertTrue(any(isinstance(exc, McpError) and exc.error.code == -32602
                            and exc.error.message == "synthetic list rejection"
                            for exc in exception_leaves(error.exception)))
        await self.assert_reaped(2)

    async def test_json_rpc_error_is_distinct_from_tool_error(self):
        async with connect_servers(self.config(peer="rpc_error")) as manager:
            with self.assertRaises(MCPToolError) as error:
                await manager.call_tool("peer__inspect", {})
            self.assertEqual(error.exception.kind, "protocol")
            self.assertEqual(error.exception.details["code"], -32602)
            self.assertIn("synthetic call rejection", str(error.exception))
        await self.assert_reaped(2)

    async def test_nontext_and_structured_content_survive_real_transport(self):
        async with connect_servers(self.config(peer="mixed")) as manager:
            result = await manager.call_tool("peer__inspect", {})
            self.assertEqual([p["type"] for p in result["content"]], ["text", "image"])
            self.assertEqual(result["content"][1]["data"], "AA==")
            self.assertEqual(result["structured_content"], {"count": 1})
        await self.assert_reaped(2)

    async def test_paginated_discovery_and_remote_name_routing(self):
        async with connect_servers(self.config(peer="paginated")) as manager:
            self.assertIn("peer__inspect_a", manager.bindings)
            self.assertIn("peer__inspect_b", manager.bindings)
            pages = [e for e in manager.events if e["event"] == "tools/list" and e["server"] == "peer"]
            self.assertEqual([e["tools"] for e in pages], [["inspect_a"], ["inspect_b"]])
            result = await manager.call_tool("peer__inspect_b", {})
            self.assertEqual(result["tool"], "inspect_b")
        await self.assert_reaped(2)

    async def test_repeated_cursor_and_external_schema_reference_are_rejected(self):
        for mode in ("repeat_cursor", "remote_ref", "output_ref"):
            with self.subTest(mode=mode):
                # Fresh config per subtest; config() mutates only this test's in-memory copy.
                self.base = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
                with self.assertRaises(Exception) as error:
                    async with connect_servers(self.config(peer=mode)):
                        self.fail("Invalid discovery metadata must not be registered")
                expected = "Repeated tools/list cursor" if mode == "repeat_cursor" else "Only in-document schema references"
                self.assertTrue(any(isinstance(exc, ConfigError) and expected in str(exc)
                                    for exc in exception_leaves(error.exception)))
                await self.assert_reaped()
                for marker in self.probes.glob("*.pid"):
                    marker.unlink()

    async def test_sdk_request_timeout_and_cleanup(self):
        async with connect_servers(self.config(timeout=1.0)) as manager:
            with self.assertRaises(MCPToolError) as error:
                await manager.call_tool("local__read_note", {"path": "note.txt", "delay_seconds": 5})
            self.assertEqual(error.exception.kind, "protocol")
        await self.assert_reaped(1)

    async def test_agent_deadline_closes_server(self):
        model = ScriptedModel([tool_response("local__read_note", {"path": "note.txt", "delay_seconds": 5})])
        async with connect_servers(self.config()) as manager:
            result = await run_agent(model, SYSTEM, TASK, manager.tools(), timeout=0.1)
            self.assertEqual(result.status, "timeout")
        await self.assert_reaped(1)

    async def test_task_cancel_during_tool_closes_server(self):
        configs = self.config()
        ready = asyncio.Event()

        async def job():
            async with connect_servers(configs) as manager:
                ready.set()
                await manager.call_tool("local__read_note", {"path": "note.txt", "delay_seconds": 5})

        task = asyncio.create_task(job())
        await asyncio.wait_for(ready.wait(), 5)
        await asyncio.sleep(0.05)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await self.assert_reaped(1)

    async def test_task_cancel_during_initialization_rolls_back_all(self):
        configs = self.config(peer="hang")

        async def job():
            async with connect_servers(configs):
                self.fail("Hanging server cannot initialize")

        task = asyncio.create_task(job())
        try:
            async with asyncio.timeout(5):
                while not (self.probes / "hang.pid").exists():
                    await asyncio.sleep(0.02)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        await self.assert_reaped(2)

    async def test_default_cli_runs_protocol_and_checks_fixture_results(self):
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(HERE / "app.py"), cwd=HERE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 10)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        self.assertEqual(process.returncode, 0, stderr.decode())
        output = stdout.decode()
        self.assertIn("mode=fixture", output)
        self.assertEqual(output.count("initialize -> protocol="), 2)
        self.assertIn("fixture.check=passed", output)
        self.assertIn("connections=closed", output)

    async def test_cli_missing_note_fails_instead_of_claiming_fixture_passed(self):
        self.config(two=True)
        empty = self.root / "empty"
        empty.mkdir()
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(HERE / "app.py"), "--workspace", str(empty),
            "--config", str(self.root / "config.json"), cwd=HERE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), 10)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        self.assertEqual(process.returncode, 1)
        self.assertNotIn("fixture.check=passed", stdout.decode())
        self.assertIn("connections=closed", stdout.decode())
        await self.assert_reaped(2)

    async def test_relative_executable_is_resolved_against_configured_cwd(self):
        child = self.root / "child"
        child.mkdir()
        executable = child / "server-program"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o700)
        config = self.root / "relative.json"
        config.write_text(json.dumps({"servers": {"local": {
            "command": "./server-program", "args": [], "cwd": "child"}}}), encoding="utf-8")
        entry = load_config(config, self.workspace)[0]
        self.assertEqual(entry.command, str(executable.resolve()))
        self.assertEqual(entry.cwd, child.resolve())
        self.assertEqual(self.pids(), [])

    async def test_config_rejects_bad_shapes_and_duplicate_keys_before_start(self):
        examples = [
            '{"servers":{},"unknown":true}',
            '{"servers":{"x":{"command":"$PYTHON","args":"-c pass"}}}',
            '{"servers":{"x":{"command":"$PYTHON","args":[],"env":{"SECRET":"value"}}}}',
            '{"servers":{"x":{"command":"$PYTHON","args":[],"timeout_seconds":true}}}',
            '{"servers":{"x":{"command":"$PYTHON","args":[],"timeout_seconds":NaN}}}',
            '{"servers":{"x":{"command":"$PYTHON","args":[]},"x":{"command":"$PYTHON","args":[]}}}',
            '{"servers":{"a__b":{"command":"$PYTHON","args":[]}}}',
            '{"servers":{"x":{"command":"definitely-missing-mcp-executable","args":[]}}}',
        ]
        for value in examples:
            with self.subTest(value=value):
                config = self.root / "invalid.json"
                config.write_text(value, encoding="utf-8")
                with self.assertRaises(ConfigError):
                    load_config(config, self.workspace)
        self.assertEqual(self.pids(), [])


if __name__ == "__main__":
    unittest.main()
