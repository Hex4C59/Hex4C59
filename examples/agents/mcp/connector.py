"""Official MCP 1.30 stdio sessions, adapted to the tutorial's Tool API.

Configuration is trusted code-launch configuration, not a sandbox policy.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import shutil
import tempfile
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import PaginatedRequestParams
from referencing import Registry

from agent_runtime import Tool


class ConfigError(ValueError):
    pass


class MCPToolError(RuntimeError):
    def __init__(self, kind: str, message: str, *, details: Any = None):
        self.kind = kind
        self.details = details
        super().__init__(f"MCP {kind}: {message}")


@dataclass(frozen=True)
class ServerConfig:
    name: str
    command: str
    args: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    timeout_seconds: float


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path: Path, workspace: Path) -> list[ServerConfig]:
    """Validate the whole document before starting any child process.

    $PYTHON selects this interpreter; {workspace} substitutes one complete arg.
    Relative cwd is relative to the config file, never the caller's directory.
    Only explicitly named environment values are forwarded, in addition to the
    SDK's documented default environment. Do not put secrets in this file.
    """
    import sys

    path = Path(path).resolve(strict=True)
    workspace = Path(workspace)
    if workspace.is_symlink() or not workspace.is_dir():
        raise ConfigError("Workspace must be an existing non-symlink directory")
    workspace = workspace.resolve()
    if path.stat().st_size > 64_000:
        raise ConfigError("Config exceeds 64000 bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ConfigError("Non-finite JSON value")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ConfigError("Config must be UTF-8 JSON") from exc
    if not isinstance(data, dict) or set(data) != {"servers"}:
        raise ConfigError("Config must contain exactly 'servers'")
    servers = data["servers"]
    if not isinstance(servers, dict) or not 1 <= len(servers) <= 8:
        raise ConfigError("Configure between 1 and 8 named servers")
    configs = []
    for name, value in servers.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,15}", name) or "__" in name:
            raise ConfigError("Server names use 1-16 lowercase letters/digits/underscores, without '__'")
        allowed = {"command", "args", "cwd", "env_from", "timeout_seconds"}
        if not isinstance(value, dict) or set(value) - allowed or not {"command", "args"} <= set(value):
            raise ConfigError(f"Invalid configuration fields: {name}")
        command = value["command"]
        args = value["args"]
        if not isinstance(command, str) or not command.strip() or "\0" in command:
            raise ConfigError(f"Invalid command: {name}")
        if not isinstance(args, list) or not all(isinstance(a, str) and "\0" not in a for a in args):
            raise ConfigError(f"args must be a string array: {name}")
        command = sys.executable if command == "$PYTHON" else command
        cwd = value.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd or "\0" in cwd:
            raise ConfigError(f"Invalid cwd: {name}")
        cwd = (path.parent / cwd).resolve()
        if not cwd.is_dir():
            raise ConfigError(f"cwd is not a directory: {name}")
        # Resolve an explicit program path against the child's cwd, rather than
        # the host's working directory. Bare program names use PATH.
        executable = str(cwd / command) if os.path.dirname(command) else command
        resolved = shutil.which(executable)
        if not resolved:
            raise ConfigError(f"Executable not found for server: {name}")
        env_from = value.get("env_from", [])
        if (not isinstance(env_from, list)
                or not all(isinstance(k, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) for k in env_from)
                or len(set(env_from)) != len(env_from)):
            raise ConfigError(f"env_from must contain distinct environment names: {name}")
        if any(k not in os.environ for k in env_from):
            raise ConfigError(f"A required environment variable is missing: {name}")
        timeout = value.get("timeout_seconds", 10.0)
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or not 0.05 <= timeout <= 60):
            raise ConfigError(f"timeout_seconds must be between 0.05 and 60: {name}")
        configs.append(ServerConfig(name, resolved,
                                    tuple(str(workspace) if a == "{workspace}" else a for a in args),
                                    cwd, {k: os.environ[k] for k in env_from}, float(timeout)))
    return configs


def require_local_refs(value):
    """Do not let discovered schemas trigger remote reference downloads."""
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in ("$ref", "$dynamicRef") and (not isinstance(nested, str) or not nested.startswith("#")):
                raise ConfigError("Only in-document schema references are supported")
            require_local_refs(nested)
    elif isinstance(value, list):
        for nested in value:
            require_local_refs(nested)


@dataclass
class Binding:
    server: str
    remote_name: str
    session: ClientSession
    schema: dict
    description: str


class MCPManager:
    def __init__(self, on_event=None):
        self.bindings: dict[str, Binding] = {}
        self.closed = False
        self.events: list[dict] = []
        self.on_event = on_event

    def emit(self, event, **data):
        entry = {"event": event, **data}
        self.events.append(entry)
        if self.on_event:
            self.on_event(entry)

    def tools(self) -> list[Tool]:
        if self.closed:
            raise MCPToolError("lifecycle", "Manager is closed")

        def handler(public_name):
            async def invoke(**arguments):
                return await self.call_tool(public_name, arguments)
            return invoke

        return [Tool(name, binding.description, copy.deepcopy(binding.schema), handler(name))
                for name, binding in self.bindings.items()]

    async def call_tool(self, public_name: str, arguments: dict) -> dict:
        if self.closed:
            raise MCPToolError("lifecycle", "Manager is closed")
        if public_name not in self.bindings:
            raise MCPToolError("routing", "Unknown namespaced tool")
        binding = self.bindings[public_name]
        Draft202012Validator(binding.schema, registry=Registry()).validate(arguments)
        try:
            result = await binding.session.call_tool(binding.remote_name, arguments)
        except McpError as exc:
            self.emit("call.error", server=binding.server, tool=binding.remote_name, kind="protocol")
            raise MCPToolError("protocol", exc.error.message,
                               details=exc.error.model_dump(mode="json")) from exc
        except Exception as exc:
            self.emit("call.error", server=binding.server, tool=binding.remote_name, kind="transport")
            raise MCPToolError("transport", type(exc).__name__) from exc
        # Keep every typed content block, including non-text blocks, and the
        # structured payload. Never turn isError into a successful tool message.
        payload = {"server": binding.server, "tool": binding.remote_name,
                   "content": [block.model_dump(mode="json", by_alias=True, exclude_none=True)
                               for block in result.content],
                   "structured_content": result.structuredContent}
        if result.isError:
            self.emit("call.error", server=binding.server, tool=binding.remote_name, kind="tool")
            texts = [block.text for block in result.content if block.type == "text"]
            raise MCPToolError("tool", "\n".join(texts) or "Server reported isError", details=payload)
        self.emit("call.ok", server=binding.server, tool=binding.remote_name)
        return payload


@asynccontextmanager
async def connect_servers(configs: list[ServerConfig], *, on_event=None):
    """Enter/exit SDK contexts in the SAME task, in reverse acquisition order.

    AsyncExitStack also unwinds previously connected servers if a later server
    fails. Do not move stack.aclose() to another task: SDK transports own AnyIO
    cancel scopes, which must be exited by their creating task.
    """
    manager = MCPManager(on_event)
    try:
        async with AsyncExitStack() as stack:
            for config in configs:
                # A real file avoids an unread stderr PIPE blocking a server.
                # It is temporary, closed on every exit, and not printed by default.
                errlog = stack.enter_context(tempfile.TemporaryFile(mode="w+t", encoding="utf-8"))
                params = StdioServerParameters(command=config.command, args=list(config.args),
                                               cwd=str(config.cwd), env=config.env)
                read, write = await stack.enter_async_context(stdio_client(params, errlog=errlog))
                session = await stack.enter_async_context(ClientSession(
                    read, write, read_timeout_seconds=timedelta(seconds=config.timeout_seconds)))
                init = await session.initialize()  # SDK negotiates version and sends initialized.
                manager.emit("initialize", server=config.name, protocol=init.protocolVersion)
                if init.capabilities.tools is None:
                    raise ConfigError(f"Server does not advertise tools: {config.name}")
                cursor = None
                seen_cursors = set()
                for _ in range(20):
                    page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor) if cursor else None)
                    manager.emit("tools/list", server=config.name, tools=[t.name for t in page.tools])
                    for remote in page.tools:
                        public = f"{config.name}__{remote.name}"
                        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", public):
                            raise ConfigError(f"Tool name is incompatible with this model adapter: {public}")
                        if public in manager.bindings or len(manager.bindings) >= 64:
                            raise ConfigError("Duplicate tool or more than 64 discovered tools")
                        if remote.outputSchema is not None:
                            require_local_refs(remote.outputSchema)
                            Draft202012Validator.check_schema(remote.outputSchema)
                        schema = copy.deepcopy(remote.inputSchema)
                        if not isinstance(schema, dict) or schema.get("type") != "object":
                            raise ConfigError(f"Tool must have an object input schema: {public}")
                        schema.setdefault("properties", {})
                        schema.setdefault("required", [])
                        if schema.get("additionalProperties") not in (None, False):
                            raise ConfigError(f"Open-ended tool arguments are not supported: {public}")
                        schema["additionalProperties"] = False
                        require_local_refs(schema)
                        Draft202012Validator.check_schema(schema)
                        manager.bindings[public] = Binding(config.name, remote.name, session, schema,
                                                           remote.description or remote.name)
                    cursor = page.nextCursor
                    if not cursor:
                        break
                    if cursor in seen_cursors:
                        raise ConfigError("Repeated tools/list cursor")
                    seen_cursors.add(cursor)
                else:
                    raise ConfigError("tools/list pagination limit exceeded")
            if not manager.bindings:
                raise ConfigError("No tools discovered")
            yield manager
    finally:
        manager.closed = True
        manager.bindings.clear()
        manager.emit("connections.closed")
