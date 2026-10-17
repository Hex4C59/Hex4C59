"""Small, testable Chat Completions tool loop for the published tutorials.

File tools are trusted local demonstrations, not an operating-system sandbox.
The timeout cancels async operations; synchronous handlers must finish promptly.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import dataclass
import inspect
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]

    def definition(self) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.name):
            raise ValueError("Tool names must contain 1–64 letters, digits, _ or -")
        Draft202012Validator.check_schema(self.parameters)
        if self.parameters.get("type") != "object":
            raise ValueError("Tool parameters must be a JSON object schema")
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": deepcopy(self.parameters),
        }}


@dataclass
class AgentResult:
    status: str
    text: str
    messages: list[dict]
    turns: int
    tool_calls: int


class ScriptedModel:
    """Explicit fixture responses. This does not simulate a model quality test."""

    def __init__(self, responses: Sequence[dict]):
        self.responses = deepcopy(list(responses))
        self.requests: list[dict] = []
        self.position = 0

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        self.requests.append({"messages": deepcopy(messages), "tools": deepcopy(tools)})
        if self.position >= len(self.responses):
            raise RuntimeError("Model fixture exhausted")
        response = deepcopy(self.responses[self.position])
        self.position += 1
        return response


def _reject_json_constant(value):
    raise ValueError("Invalid JSON constant: " + value)


class OpenAIChatModel:
    """Optional live adapter. No network call is made by offline fixture demos."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not api_key or not model:
            raise ValueError("Live mode requires OPENAI_API_KEY and OPENAI_MODEL")
        from openai import AsyncOpenAI
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url,
                                  timeout=20.0, max_retries=0)

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        result = await self.client.chat.completions.create(**kwargs)
        if not result.choices:
            raise RuntimeError("Model returned no choices")
        choice = result.choices[0]
        if choice.finish_reason not in {"stop", "tool_calls"}:
            raise RuntimeError("Incomplete model response: " + str(choice.finish_reason))
        message = choice.message.model_dump(exclude_none=True)
        return {key: message[key] for key in ("role", "content", "tool_calls") if key in message}

    async def aclose(self) -> None:
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.aclose()


def model_from_env() -> OpenAIChatModel:
    return OpenAIChatModel(os.environ.get("OPENAI_API_KEY", ""),
                           os.environ.get("OPENAI_MODEL", ""),
                           os.environ.get("OPENAI_BASE_URL") or None)


async def run_agent(model, system: str, task: str, tools: list[Tool], *,
                    max_turns: int = 8, max_tool_calls: int = 32,
                    timeout: float = 60.0, on_event=None) -> AgentResult:
    """Execute validated tool calls in order, exposing failures to the model.

    Tool error messages are data, not success. Tool output is capped to keep an
    accidental large result from consuming unbounded context. This is not a token
    estimator or a policy for a particular model's context window.
    """
    if max_turns < 1 or max_tool_calls < 1 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Limits must be positive and timeout must be finite")
    definitions = [tool.definition() for tool in tools]
    registry = {tool.name: tool for tool in tools}
    if len(registry) != len(tools):
        raise ValueError("Duplicate tool name")
    messages: list[dict] = [{"role": "system", "content": system},
                            {"role": "user", "content": task}]
    turns = calls = 0
    started = time.monotonic()

    async def emit(event: str, **fields):
        if on_event is not None:
            pending = on_event({"event": event, "elapsed_ms": round((time.monotonic()-started)*1000),
                                **fields})
            if inspect.isawaitable(pending):
                await pending

    async def finish(status: str, text: str) -> AgentResult:
        await emit("run.end", status=status, turns=turns, tool_calls=calls)
        return AgentResult(status, text, messages, turns, calls)

    try:
        async with asyncio.timeout(timeout):
            await emit("run.start")
            for turn in range(1, max_turns + 1):
                turns = turn
                await emit("model.start", turn=turn)
                response = await model.complete(deepcopy(messages), deepcopy(definitions))
                if not isinstance(response, dict) or response.get("role", "assistant") != "assistant":
                    return await finish("error", "Model response must be an assistant message")
                content = response.get("content")
                if content is not None and not isinstance(content, str):
                    return await finish("error", "Assistant content must be text or null")
                requested = response.get("tool_calls") or []
                if not isinstance(requested, list):
                    return await finish("error", "tool_calls must be a list")
                ids = set()
                for call in requested:
                    if (not isinstance(call, dict) or not isinstance(call.get("id"), str)
                            or not call["id"] or call["id"] in ids
                            or call.get("type") != "function"
                            or not isinstance(call.get("function"), dict)):
                        return await finish("error", "Malformed or duplicate tool call")
                    ids.add(call["id"])
                normalized = {"role": "assistant", "content": content}
                if requested:
                    normalized["tool_calls"] = requested
                messages.append(normalized)
                await emit("model.end", turn=turn, requested_tools=len(requested))
                if not requested:
                    if content is None:
                        return await finish("error", "Model returned neither text nor tools")
                    return await finish("complete", content)
                for call in requested:
                    if calls >= max_tool_calls:
                        return await finish("limit", "Tool call limit reached; work is incomplete")
                    calls += 1
                    name = call["function"].get("name")
                    name_for_trace = name if isinstance(name, str) else "<invalid>"
                    await emit("tool.start", turn=turn, tool=name_for_trace, call_id=call["id"])
                    ok = False
                    try:
                        if not isinstance(name, str) or name not in registry:
                            raise ValueError("Unknown tool")
                        raw = call["function"].get("arguments")
                        if not isinstance(raw, str) or len(raw) > 100_000:
                            raise ValueError("Tool arguments must be a JSON string of at most 100000 characters")
                        arguments = json.loads(raw, parse_constant=_reject_json_constant)
                        tool = registry[name]
                        Draft202012Validator(tool.parameters).validate(arguments)
                        value = tool.handler(**arguments)
                        if inspect.isawaitable(value):
                            value = await value
                        payload = {"ok": True, "result": value}
                        # Refuse non-JSON results, including NaN, before returning success.
                        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
                        if len(encoded) > 32_000:
                            raise ValueError("Tool result exceeds 32000 characters; narrow the request")
                        ok = True
                    except Exception as error:
                        detail = error.message if isinstance(error, ValidationError) else str(error)
                        encoded = json.dumps({"ok": False, "error": detail[:1200],
                                              "error_type": type(error).__name__}, ensure_ascii=False)
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": encoded})
                    await emit("tool.end", turn=turn, tool=name_for_trace, call_id=call["id"], ok=ok)
            return await finish("limit", "Turn limit reached; work is incomplete")
    except TimeoutError:
        return await finish("timeout", "Run deadline reached; work is incomplete")
    except asyncio.CancelledError:
        await emit("run.end", status="cancelled", turns=turns, tool_calls=calls)
        raise
    except Exception as error:
        # Provider errors can contain request bodies. Do not expose them in logs.
        return await finish("error", "Run failed: " + type(error).__name__)


def confined_path(root: Path, relative: str, *, allow_root: bool = False) -> Path:
    """Reject traversal and symlink components in a trusted local workspace.

    Does not defend against another process racing to replace directories. Keep
    workspaces private and do not use it as isolation for hostile local programs.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Workspace must be an existing, non-symlink directory")
    root = root.resolve()
    if not isinstance(relative, str) or "\x00" in relative or "\\" in relative:
        raise ValueError("Use a relative path with / separators")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Absolute paths and parent traversal are forbidden")
    target = root / candidate
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink paths are forbidden")
    resolved = target.resolve()
    if not resolved.is_relative_to(root) or (resolved == root and not allow_root):
        raise ValueError("Path must remain inside the workspace")
    return target


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    if path.is_symlink() or not path.parent.is_dir():
        raise ValueError("Destination parent must exist and target must not be a symlink")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                          prefix=".agent-write-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
