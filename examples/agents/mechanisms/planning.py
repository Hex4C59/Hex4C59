"""Bounded async Plan-and-Execute with explicit execution/verification status.

The shared model protocol is asynchronous. Verification callbacks must check the
application's evidence; model text by itself is not a completion criterion.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import inspect
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Callable

from agent_runtime import AgentResult, ScriptedModel, Tool, atomic_write_text, confined_path, run_agent
from context_budget import BudgetedModel, ContextBudgetError, canonical


class PlanValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    depends_on: tuple[str, ...]
    success_criteria: str
    tools_needed: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionPlan:
    goal: str
    definition_of_done: str
    steps: tuple[PlanStep, ...]
    constraints: tuple[str, ...] = ()


@dataclass
class StepRecord:
    step: PlanStep
    status: str = "pending"
    summary: str = ""
    tool_calls: int = 0


@dataclass(frozen=True)
class PlanningLimits:
    max_steps: int = 8
    max_replans: int = 2
    timeout: float = 10.0
    step_timeout: float = 2.0
    max_turns_per_step: int = 4
    max_tool_calls_per_step: int = 8
    max_plan_steps: int = 16
    max_request_characters: int = 16000

    def __post_init__(self):
        for name in ("max_steps", "max_turns_per_step", "max_tool_calls_per_step", "max_plan_steps"):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 64:
                raise ValueError(f"{name} must be an integer from 1 to 64")
        if type(self.max_replans) is not int or not 0 <= self.max_replans <= 16:
            raise ValueError("max_replans must be an integer from 0 to 16")
        for name in ("timeout", "step_timeout"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if type(self.max_request_characters) is not int or self.max_request_characters < 1:
            raise ValueError("max_request_characters must be positive")


@dataclass
class PlanResult:
    goal: str
    status: str = "failed"
    phase: str = "planning"
    reason: str = ""
    plan: ExecutionPlan | None = None
    steps: list[StepRecord] = field(default_factory=list)
    attempts: int = 0
    replans: int = 0
    revisions: list[dict] = field(default_factory=list)
    request_characters: list[int] = field(default_factory=list)
    text: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _text(value, name: str, *, maximum: int = 2000, blank: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not blank and not value.strip()):
        raise PlanValidationError(f"invalid {name}")
    return value


def _parse_steps(data, completed: set[str], available: set[str], maximum: int) -> tuple[PlanStep, ...]:
    if not isinstance(data, list) or not 1 <= len(data) <= maximum:
        raise PlanValidationError("plan must contain a bounded, nonempty steps list")
    steps = []
    for item in data:
        if not isinstance(item, dict) or set(item) != {"id", "description", "depends_on", "success_criteria", "tools_needed"}:
            raise PlanValidationError("invalid step fields; models cannot set execution status")
        identifier = _text(item["id"], "step id", maximum=64)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
            raise PlanValidationError("invalid step id")
        dependencies = item["depends_on"]
        needed = item["tools_needed"]
        if (not isinstance(dependencies, list) or not all(isinstance(v, str) for v in dependencies)
                or len(dependencies) > maximum or len(set(dependencies)) != len(dependencies)
                or not isinstance(needed, list) or not all(isinstance(v, str) for v in needed)
                or len(needed) > len(available) or len(set(needed)) != len(needed)):
            raise PlanValidationError("invalid dependencies or tool list")
        if not set(needed) <= available:
            raise PlanValidationError("plan names an unavailable tool")
        steps.append(PlanStep(identifier, _text(item["description"], "description"), tuple(dependencies),
                              _text(item["success_criteria"], "success criteria"), tuple(needed)))
    ids = [step.id for step in steps]
    if len(ids) != len(set(ids)) or set(ids) & completed:
        raise PlanValidationError("duplicate step id or replacement of a completed step")
    known = completed | set(ids)
    if any(not set(step.depends_on) <= known or step.id in step.depends_on for step in steps):
        raise PlanValidationError("unknown or self dependency")
    reached = set(completed)
    while True:
        ready = {step.id for step in steps if set(step.depends_on) <= reached} - reached
        if not ready:
            break
        reached.update(ready)
    if not set(ids) <= reached:
        raise PlanValidationError("dependency cycle")
    return tuple(steps)


async def _object(model, instruction: str, payload: dict) -> dict:
    response = await model.complete([{"role": "system", "content": instruction},
                                     {"role": "user", "content": canonical(payload)}], [])
    if (not isinstance(response, dict) or response.get("role", "assistant") != "assistant"
            or response.get("tool_calls") or not isinstance(response.get("content"), str)
            or len(response["content"]) > 32000):
        raise PlanValidationError("planner/checkpoint must return bounded JSON text without tools")
    def invalid_constant(_):
        raise PlanValidationError("non-finite JSON constant")
    try:
        data = json.loads(response["content"], parse_constant=invalid_constant)
    except (json.JSONDecodeError, TypeError) as exc:
        raise PlanValidationError("malformed planner/checkpoint JSON") from exc
    if not isinstance(data, dict):
        raise PlanValidationError("planner/checkpoint output must be an object")
    return data


async def _checked(callback: Callable, *arguments) -> bool:
    answer = callback(*arguments)
    if inspect.isawaitable(answer):
        answer = await answer
    if type(answer) is not bool:
        raise PlanValidationError("verifier must return a boolean, not success-like text")
    return answer


def _tool_failure(result: AgentResult) -> bool:
    for message in result.messages:
        if message.get("role") == "tool":
            try:
                payload = json.loads(message["content"])
            except (KeyError, json.JSONDecodeError, TypeError):
                return True
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                return True
    return False


async def run_plan_and_execute(goal: str, model, tools: list[Tool], *,
                               verify_step: Callable, verify_goal: Callable,
                               context: str = "", limits: PlanningLimits | None = None) -> PlanResult:
    """Run one bounded plan; callbacks verify_step(step, AgentResult), verify_goal(plan, records).

    Timeout/failure/limit never become complete. One overall asyncio deadline covers
    planning, execution, checkpointing and both verifiers. Replans replace only pending
    steps; max_steps counts actual attempts across all revisions. Cancellation from the
    caller propagates. Async deadlines require cooperative awaits, not blocking callbacks.
    """
    limits = limits or PlanningLimits()
    result = PlanResult(goal=goal)
    bounded = BudgetedModel(model, max_characters=limits.max_request_characters)
    active: StepRecord | None = None
    overall_deadline = None

    def finish(status: str, reason: str) -> PlanResult:
        result.status = status
        result.reason = reason
        result.request_characters = [report.after for report in bounded.reports]
        if status == "complete":
            result.phase = "finished"
            result.text = "\n".join(record.summary for record in result.steps if record.status == "complete")
        return result

    try:
        _text(goal, "goal", maximum=2000)
        _text(context, "context", maximum=4000, blank=True)
        available = {tool.name for tool in tools}
        if len(available) != len(tools):
            raise PlanValidationError("duplicate tool name")
        deadline = asyncio.get_running_loop().time() + limits.timeout
        overall_deadline = asyncio.timeout_at(deadline)
        async with overall_deadline:
            initial = await _object(bounded,
                "Return JSON only: goal, definition_of_done, constraints (string list), steps. "
                "Each step has exactly id,description,depends_on,success_criteria,tools_needed. "
                "Use only available tools. Do not mark steps complete.",
                {"goal": goal, "context": context, "available_tools": sorted(available),
                 "max_plan_steps": limits.max_plan_steps})
            if set(initial) != {"goal", "definition_of_done", "constraints", "steps"} or initial["goal"] != goal:
                raise PlanValidationError("planner must preserve the original goal and required fields")
            constraints = initial["constraints"]
            if not isinstance(constraints, list) or len(constraints) > 16:
                raise PlanValidationError("invalid constraints")
            constraints = tuple(_text(item, "constraint", maximum=500) for item in constraints)
            steps = _parse_steps(initial["steps"], set(), available, limits.max_plan_steps)
            result.plan = ExecutionPlan(goal, _text(initial["definition_of_done"], "definition of done"), steps, constraints)
            result.steps = [StepRecord(step) for step in steps]
            while True:
                pending = [record for record in result.steps if record.status == "pending"]
                completed = {record.step.id for record in result.steps if record.status == "complete"}
                if not pending:
                    result.phase = "verification"
                    if not await _checked(verify_goal, result.plan, tuple(result.steps)):
                        return finish("failed", "goal_verification_failed")
                    return finish("complete", "verified")
                if result.attempts >= limits.max_steps:
                    return finish("limit", "step_limit")
                ready = [record for record in pending if set(record.step.depends_on) <= completed]
                if not ready:
                    return finish("failed", "no_runnable_step")
                active = ready[0]
                active.status = "running"
                result.attempts += 1
                result.phase = "execution"
                selected_tools = [tool for tool in tools if tool.name in active.step.tools_needed]
                try:
                    step_deadline = asyncio.timeout(limits.step_timeout)
                    async with step_deadline:
                        outcome = await run_agent(bounded,
                            "Execute only this plan step. Use tools for evidence; do not claim success from an error.",
                            canonical({"goal": goal, "definition_of_done": result.plan.definition_of_done,
                                       "constraints": list(result.plan.constraints), "step": asdict(active.step),
                                       "completed": [{"id": record.step.id, "summary": record.summary}
                                                     for record in result.steps if record.status == "complete"]}),
                            selected_tools, max_turns=limits.max_turns_per_step,
                            max_tool_calls=limits.max_tool_calls_per_step,
                            timeout=limits.step_timeout)
                        active.summary = outcome.text[:2000]
                        active.tool_calls = outcome.tool_calls
                        if outcome.status != "complete":
                            active.status = {"limit": "limit", "timeout": "timeout"}.get(outcome.status, "failed")
                            return finish(active.status, "step_" + outcome.status)
                        if _tool_failure(outcome):
                            active.status = "failed"
                            return finish("failed", "tool_error")
                        result.phase = "verification"
                        if not await _checked(verify_step, active.step, outcome):
                            active.status = "failed"
                            return finish("failed", "step_verification_failed")
                except TimeoutError:
                    active.status = "timeout"
                    return finish("timeout", "step_deadline" if step_deadline.expired() else "step_timeout")
                active.status = "complete"
                result.phase = "checkpoint"
                update = await _object(bounded,
                    "Return exactly action ('continue' or 'replan'), reason (text), pending_steps. "
                    "For continue pending_steps must be null. For replan supply a nonempty list using "
                    "the original step fields; replace pending only, never completed. No early-finish flag.",
                    {"goal": goal, "definition_of_done": result.plan.definition_of_done,
                     "just_verified": active.step.id, "records": [asdict(record) for record in result.steps],
                     "remaining_replans": limits.max_replans - result.replans})
                if set(update) != {"action", "reason", "pending_steps"}:
                    raise PlanValidationError("invalid checkpoint fields")
                reason = _text(update["reason"], "checkpoint reason", maximum=1000)
                if update["action"] == "continue":
                    if update["pending_steps"] is not None:
                        raise PlanValidationError("continue cannot replace pending steps")
                elif update["action"] == "replan":
                    if result.replans >= limits.max_replans:
                        return finish("limit", "replan_limit")
                    done = [record for record in result.steps if record.status == "complete"]
                    replacement = _parse_steps(update["pending_steps"], {r.step.id for r in done},
                                               available, limits.max_plan_steps - len(done))
                    result.revisions.append({"reason": reason,
                        "old_pending": [r.step.id for r in result.steps if r.status == "pending"],
                        "new_pending": [step.id for step in replacement]})
                    result.steps = done + [StepRecord(step) for step in replacement]
                    result.plan = ExecutionPlan(goal, result.plan.definition_of_done,
                                                tuple(r.step for r in result.steps), constraints)
                    result.replans += 1
                else:
                    raise PlanValidationError("unknown checkpoint action")
                active = None
    except TimeoutError:
        if active is not None and active.status == "running":
            active.status = "timeout"
        return finish("timeout", "overall_deadline" if overall_deadline is not None and overall_deadline.expired()
                      else "operation_timeout")
    except asyncio.CancelledError:
        if active is not None and active.status == "running":
            active.status = "cancelled"
        raise
    except ContextBudgetError:
        if active is not None and active.status == "running":
            active.status = "failed"
        return finish("failed", "context_budget")
    except PlanValidationError:
        if active is not None and active.status == "running":
            active.status = "failed"
        return finish("failed", "invalid_plan_or_checkpoint")
    except Exception as exc:
        if active is not None and active.status == "running":
            active.status = "failed"
        return finish("failed", "operation_error:" + type(exc).__name__)


def _step(identifier, description, dependencies=(), tools=()):
    return {"id": identifier, "description": description, "depends_on": list(dependencies),
            "success_criteria": "Check the synthetic file evidence.", "tools_needed": list(tools)}


def _json_message(data: dict) -> dict:
    return {"role": "assistant", "content": canonical(data)}


def _tool_message(name, arguments, number):
    return {"role": "assistant", "content": None, "tool_calls": [{"id": f"call_{number}",
        "type": "function", "function": {"name": name, "arguments": canonical(arguments)}}]}


async def demo() -> dict:
    """Fixed model, actual file tools, evidence checks, one replan; tempdir is owned here."""
    goal = "Write and verify synthetic source, then create its verification report."
    with tempfile.TemporaryDirectory(prefix="planning-mechanism-") as directory:
        root = Path(directory)
        def write_note(path, content):
            atomic_write_text(confined_path(root, path), content)
            return {"written": path}
        def read_note(path):
            return {"content": confined_path(root, path).read_text(encoding="utf-8")}
        path_schema = {"type": "string", "enum": ["source.txt", "verified.txt"]}
        tools = [
            Tool("write_note", "Write a synthetic note in this temporary demo.", {
                "type": "object", "properties": {"path": path_schema, "content": {"type": "string", "maxLength": 100}},
                "required": ["path", "content"], "additionalProperties": False}, write_note),
            Tool("read_note", "Read synthetic temporary evidence.", {
                "type": "object", "properties": {"path": path_schema},
                "required": ["path"], "additionalProperties": False}, read_note),
        ]
        initial = {"goal": goal, "definition_of_done": "Source and verified report contain the expected synthetic evidence.",
                   "constraints": ["Only synthetic data in the temporary workspace."], "steps": [
                       _step("write", "Write source.txt", tools=("write_note",)),
                       _step("report", "Write verified.txt", ("write",), ("write_note",))]}
        replan = {"action": "replan", "reason": "Read back source evidence before reporting.", "pending_steps": [
            _step("verify", "Read and verify source.txt", ("write",), ("read_note",)),
            _step("report", "Write verified.txt after checking source", ("verify",), ("write_note",))]}
        keep = {"action": "continue", "reason": "Evidence checked; keep remaining plan.", "pending_steps": None}
        scripted = ScriptedModel([
            _json_message(initial), _tool_message("write_note", {"path": "source.txt", "content": "synthetic evidence"}, 1),
            {"role": "assistant", "content": "fixture source written"}, _json_message(replan),
            _tool_message("read_note", {"path": "source.txt"}, 2),
            {"role": "assistant", "content": "fixture source read"}, _json_message(keep),
            _tool_message("write_note", {"path": "verified.txt", "content": "verified synthetic evidence"}, 3),
            {"role": "assistant", "content": "fixture report written"}, _json_message(keep),
        ])
        async def verify_step(step, outcome):
            if step.id == "write":
                return (root / "source.txt").read_text() == "synthetic evidence"
            if step.id == "verify":
                results = [json.loads(m["content"]) for m in outcome.messages if m["role"] == "tool"]
                return any(item.get("result", {}).get("content") == "synthetic evidence" for item in results)
            return (root / "verified.txt").read_text() == "verified synthetic evidence"
        async def verify_goal(plan, records):
            return ({record.step.id for record in records if record.status == "complete"} == {"write", "verify", "report"}
                    and (root / "verified.txt").read_text() == "verified synthetic evidence")
        result = await run_plan_and_execute(goal, scripted, tools, verify_step=verify_step,
                                           verify_goal=verify_goal, limits=PlanningLimits(timeout=3.0, step_timeout=1.0))
        assert result.status == "complete", result.as_dict()
        assert result.attempts == 3 and result.replans == 1
        completed = [record.step.id for record in result.steps if record.status == "complete"]
        assert completed == ["write", "verify", "report"]
        assert result.revisions[0]["old_pending"] == ["report"]
        assert all(n <= 16000 for n in result.request_characters)
    assert not root.exists()
    return {"ok": True, "mode": "fixture", "status": result.status,
            "completed_steps": completed, "attempts": result.attempts, "replans": result.replans,
            "model_calls": len(scripted.requests), "files_verified": True,
            "temporary_workspace_removed": True, "max_request_characters": max(result.request_characters)}
