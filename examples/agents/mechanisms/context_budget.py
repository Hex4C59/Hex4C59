"""Measured character budget for messages/tools; preserves protocol and current task.

No tokenizer or model-quality claim: units are Unicode code points in canonical JSON.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any

from agent_runtime import ScriptedModel, Tool, run_agent


class ContextBudgetError(ValueError):
    """A valid, required input cannot fit, or its tool protocol is malformed."""


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContextBudgetError("request must contain finite JSON data") from exc


def request_characters(messages: list[dict], tools: list[dict]) -> int:
    return len(canonical({"messages": messages, "tools": tools}))


@dataclass(frozen=True)
class BudgetReport:
    before: int
    after: int
    limit: int
    dropped_messages: int
    dropped_turns: int
    dropped_exchanges: int


@dataclass(frozen=True)
class PreparedContext:
    messages: list[dict]
    report: BudgetReport


@dataclass(frozen=True)
class _Unit:
    indices: tuple[int, ...]
    role: str
    exchange: bool = False


def _units(messages: list[dict]) -> list[_Unit]:
    """Validate complete exchanges, including null assistant content/multiple calls."""
    units = []
    index = 0
    while index < len(messages):
        message = messages[index]
        if not isinstance(message, dict):
            raise ContextBudgetError("each message must be an object")
        role = message.get("role")
        if not isinstance(role, str) or role not in {"system", "developer", "user", "assistant", "tool"}:
            raise ContextBudgetError("unknown message role")
        content = message.get("content")
        if role == "assistant":
            if content is not None and not isinstance(content, str):
                raise ContextBudgetError("assistant content must be text or null")
        elif not isinstance(content, str):
            raise ContextBudgetError("message content must be text")
        if role == "tool":
            raise ContextBudgetError("orphan tool result")
        if "tool_calls" in message and role != "assistant":
            raise ContextBudgetError("tool_calls must belong to an assistant")
        calls = message.get("tool_calls")
        if calls:
            if role != "assistant" or not isinstance(calls, list):
                raise ContextBudgetError("tool calls must belong to an assistant")
            ids = set()
            for call in calls:
                if (not isinstance(call, dict) or not isinstance(call.get("id"), str)
                        or not call["id"] or call["id"] in ids or call.get("type") != "function"
                        or not isinstance(call.get("function"), dict)
                        or not isinstance(call["function"].get("name"), str)
                        or not isinstance(call["function"].get("arguments"), str)):
                    raise ContextBudgetError("malformed or duplicate tool call")
                ids.add(call["id"])
            indices = [index]
            cursor = index + 1
            pending = set(ids)
            while pending:
                if cursor >= len(messages):
                    raise ContextBudgetError("tool exchange has missing results")
                result = messages[cursor]
                if (not isinstance(result, dict) or result.get("role") != "tool"
                        or not isinstance(result.get("tool_call_id"), str)
                        or result.get("tool_call_id") not in pending
                        or not isinstance(result.get("content"), str)):
                    raise ContextBudgetError("tool results must match each call exactly once")
                pending.remove(result["tool_call_id"])
                indices.append(cursor)
                cursor += 1
            units.append(_Unit(tuple(indices), role, True))
            index = cursor
        else:
            if calls is not None and calls != []:
                raise ContextBudgetError("tool_calls must be a list")
            units.append(_Unit((index,), role))
            index += 1
    return units


def fit_context(messages: list[dict], tools: list[dict], *, max_characters: int = 16000,
                required_task: str | None = None) -> PreparedContext:
    """Remove old whole user turns, then old complete exchanges in the active turn.

    All system/developer messages, the latest user task, and the newest active
    assistant/exchange are required. An unfit required input raises before delegation.
    The input objects are never changed. This controls requests, not external archives.
    """
    if type(max_characters) is not int or max_characters < 1:
        raise ContextBudgetError("max_characters must be a positive integer")
    if not isinstance(messages, list) or not messages or not isinstance(tools, list):
        raise ContextBudgetError("messages and tools must be lists")
    units = _units(messages)
    user_units = [i for i, unit in enumerate(units) if unit.role == "user"]
    if not user_units:
        raise ContextBudgetError("a current user task is required")
    current = user_units[-1]
    current_text = messages[units[current].indices[0]]["content"]
    if not current_text.strip() or (required_task is not None and current_text != required_task):
        raise ContextBudgetError("latest user message must contain the required current task")
    pinned = {i for i, unit in enumerate(units) if unit.role in {"system", "developer"}}
    pinned.add(current)
    active = [i for i in range(current + 1, len(units)) if i not in pinned]
    if active:
        pinned.add(active[-1])
    # A candidate is one complete historical user turn or one active atomic unit.
    candidates: list[tuple[list[int], bool]] = []
    cursor = 0
    for user_index in user_units:
        if user_index >= current:
            break
        if cursor < user_index:
            loose = [i for i in range(cursor, user_index) if i not in pinned]
            if loose:
                candidates.append((loose, False))
        next_user = next(i for i in user_units if i > user_index)
        turn = [i for i in range(user_index, next_user) if i not in pinned]
        if turn:
            candidates.append((turn, True))
        cursor = next_user
    if cursor < current:
        loose = [i for i in range(cursor, current) if i not in pinned]
        if loose:
            candidates.append((loose, False))
    for i in active:
        if i not in pinned:
            candidates.append(([i], False))
    before = request_characters(messages, tools)
    dropped: set[int] = set()
    dropped_turns = dropped_exchanges = 0

    def outgoing() -> list[dict]:
        removed_indices = {j for i in dropped for j in units[i].indices}
        result = [deepcopy(message) for j, message in enumerate(messages) if j not in removed_indices]
        if dropped:
            result.insert(0, {"role": "system", "content":
                f"Context controller omitted {len(removed_indices)} historical messages as whole units. "
                "Re-read evidence if needed; omission is not proof of completion."})
        return result

    prepared = outgoing()
    for candidate, is_turn in candidates:
        if request_characters(prepared, tools) <= max_characters:
            break
        fresh = [i for i in candidate if i not in dropped]
        dropped.update(fresh)
        dropped_turns += int(is_turn and bool(fresh))
        dropped_exchanges += sum(units[i].exchange for i in fresh)
        prepared = outgoing()
    measured = request_characters(prepared, tools)
    if measured > max_characters:
        raise ContextBudgetError("required task, instructions, schemas or newest exchange exceed character budget")
    report = BudgetReport(before, measured, max_characters,
                          sum(len(units[i].indices) for i in dropped),
                          dropped_turns, dropped_exchanges)
    return PreparedContext(prepared, report)


class BudgetedModel:
    """Shared-runtime model protocol with pre-call validation and bounded audit data."""

    def __init__(self, model, *, max_characters: int = 16000, required_task: str | None = None):
        if type(max_characters) is not int or max_characters < 1:
            raise ContextBudgetError("max_characters must be a positive integer")
        self.model = model
        self.max_characters = max_characters
        self.required_task = required_task
        self.reports: deque[BudgetReport] = deque(maxlen=64)
        self.calls = 0

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        prepared = fit_context(messages, tools, max_characters=self.max_characters,
                               required_task=self.required_task)
        self.reports.append(prepared.report)
        self.calls += 1
        return await self.model.complete(prepared.messages, deepcopy(tools))


def _call(names: list[str], group: int) -> dict:
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": f"call_{group}_{i}", "type": "function", "function": {
            "name": "read_fixture", "arguments": canonical({"name": name})}}
        for i, name in enumerate(names)]}


async def demo() -> dict:
    """Real validated loop/compaction with fixed responses; owns no external state."""
    observed = []
    def read_fixture(name):
        observed.append(name)
        return {"name": name, "synthetic_data": "资料" * 480}
    tools = [Tool("read_fixture", "Return bounded synthetic fixture evidence.", {
        "type": "object", "properties": {"name": {"type": "string", "maxLength": 20}},
        "required": ["name"], "additionalProperties": False}, read_fixture)]
    scripted = ScriptedModel([_call(["one", "two"], 1), _call(["three"], 2),
                              _call(["four"], 3), {"role": "assistant", "content": "fixture 完成"}])
    task = "保留这个当前任务，读取四份合成资料。"
    model = BudgetedModel(scripted, max_characters=3700, required_task=task)
    result = await run_agent(model, "fixture：上下文预算演示。", task, tools, max_turns=6, timeout=2.0)
    assert result.status == "complete", result.text
    assert observed == ["one", "two", "three", "four"]
    assert any(report.dropped_exchanges for report in model.reports)
    for request, report in zip(scripted.requests, model.reports):
        assert report.after == request_characters(**request) <= model.max_characters
        assert any(m.get("role") == "user" and m.get("content") == task for m in request["messages"])
        _units(request["messages"])
    return {"ok": True, "mode": "fixture", "status": result.status,
            "model_calls": model.calls, "tools_executed": observed,
            "max_request_characters": max(report.after for report in model.reports),
            "limit_characters": model.max_characters,
            "dropped_exchanges": sum(report.dropped_exchanges for report in model.reports),
            "current_task_preserved": True, "complete_tool_exchanges": True}
