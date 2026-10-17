"""Async deadline/state and whole-exchange budget tests; no network or personal data."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import unittest

from agent_runtime import ScriptedModel, Tool, run_agent
import context_budget as cb
import planning as pl


GOAL = "Complete synthetic work with checked evidence."


def step(name, dependencies=(), tools=()):
    return {"id": name, "description": f"Do synthetic {name}", "depends_on": list(dependencies),
            "success_criteria": "The deterministic verifier accepts the evidence.", "tools_needed": list(tools)}


def initial(*steps):
    return {"goal": GOAL, "definition_of_done": "All synthetic evidence verified.", "constraints": [], "steps": list(steps)}


def message(content):
    return {"role": "assistant", "content": cb.canonical(content) if isinstance(content, dict) else content}


def keep():
    return message({"action": "continue", "reason": "Keep remaining steps.", "pending_steps": None})


def replan(*steps):
    return message({"action": "replan", "reason": "New synthetic evidence.", "pending_steps": list(steps)})


def exchange(ids=("one",), text="evidence"):
    calls = [{"id": identifier, "type": "function", "function": {"name": "read", "arguments": "{}"}}
             for identifier in ids]
    return [{"role": "assistant", "content": None, "tool_calls": calls}] + [
        {"role": "tool", "tool_call_id": identifier, "content": text} for identifier in ids]


async def accepted(*_):
    return True


class ContextTests(unittest.TestCase):
    def test_old_user_turn_and_multicall_exchange_are_removed_as_whole_units(self):
        messages = [{"role": "system", "content": "Keep instruction"},
                    {"role": "user", "content": "old task"}, *exchange(("a", "b"), "x" * 1800),
                    {"role": "assistant", "content": "old answer"},
                    {"role": "user", "content": "REQUIRED CURRENT TASK"}]
        original = deepcopy(messages)
        fitted = cb.fit_context(messages, [], max_characters=1000, required_task="REQUIRED CURRENT TASK")
        self.assertEqual(messages, original)
        self.assertEqual(fitted.report.dropped_turns, 1)
        self.assertEqual(fitted.report.dropped_exchanges, 1)
        self.assertFalse(any(m["role"] == "tool" for m in fitted.messages))
        self.assertEqual(fitted.messages[-1], messages[-1])
        self.assertIn(messages[0], fitted.messages)
        self.assertLessEqual(cb.request_characters(fitted.messages, []), 1000)

    def test_current_task_and_latest_null_content_multi_tool_group_stay_exact(self):
        latest = exchange(("new1", "new2"), "new evidence")
        messages = [{"role": "system", "content": "system"},
                    {"role": "user", "content": "current task"},
                    *exchange(("old",), "x" * 3000), *latest]
        fitted = cb.fit_context(messages, [], max_characters=1400)
        self.assertEqual(fitted.messages[-3:], latest)
        self.assertIn(messages[1], fitted.messages)
        self.assertEqual(fitted.report.dropped_exchanges, 1)

    def test_latest_exchange_cannot_be_split_to_make_it_fit(self):
        messages = [{"role": "user", "content": "task"}, *exchange(("one", "two"), "x" * 3000)]
        with self.assertRaises(cb.ContextBudgetError):
            cb.fit_context(messages, [], max_characters=1000)

    def test_pinned_system_developer_task_and_schemas_all_count_toward_budget(self):
        messages = [{"role": "system", "content": "system instruction"},
                    {"role": "developer", "content": "required instruction"},
                    {"role": "user", "content": "current Chinese 中文 task"}]
        tools = [{"type": "function", "function": {"name": "read", "description": "x" * 5000}}]
        before = deepcopy(messages)
        with self.assertRaises(cb.ContextBudgetError):
            cb.fit_context(messages, tools, max_characters=1000)
        self.assertEqual(messages, before)
        with self.assertRaises(cb.ContextBudgetError):
            cb.fit_context(messages, [], required_task="a different task")
        exact = cb.request_characters(messages, [])
        fitted = cb.fit_context(messages, [], max_characters=exact)
        self.assertEqual(fitted.messages, messages)
        self.assertEqual(fitted.report.after, exact)

    def test_orphan_missing_duplicate_and_interleaved_tool_results_are_rejected(self):
        prefix = [{"role": "user", "content": "task"}]
        group = exchange(("a", "b"))
        invalid = [
            prefix + [{"role": "tool", "tool_call_id": "a", "content": "orphan"}],
            prefix + group[:-1],
            prefix + [group[0], group[1], group[1]],
            prefix + [group[0], {"role": "user", "content": "interrupt"}, *group[1:]],
        ]
        for messages in invalid:
            with self.subTest(messages=messages), self.assertRaises(cb.ContextBudgetError):
                cb.fit_context(messages, [], max_characters=99999)

    def test_invalid_numbers_and_no_current_user_are_not_silently_repaired(self):
        for messages in ([{"role": "system", "content": "no user"}],
                         [{"role": "user", "content": " "}],
                         [{"role": "user", "content": "task", "bad": float("nan")}],
                         [{"role": [], "content": "invalid"}],
                         [{"role": "user", "content": "task"}, {"role": "assistant", "content": 42}]):
            with self.subTest(messages=messages), self.assertRaises(cb.ContextBudgetError):
                cb.fit_context(messages, [])


class ContextAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_demo_executes_tools_and_validates_real_pre_call_compaction(self):
        result = await cb.demo()
        self.assertTrue(result["ok"])
        self.assertEqual(result["tools_executed"], ["one", "two", "three", "four"])
        self.assertGreater(result["dropped_exchanges"], 0)

    async def test_unfit_required_task_never_reaches_underlying_model(self):
        base = ScriptedModel([message("must not run")])
        model = cb.BudgetedModel(base, max_characters=100)
        with self.assertRaises(cb.ContextBudgetError):
            await model.complete([{"role": "user", "content": "x" * 1000}], [])
        self.assertEqual(base.requests, [])
        self.assertEqual(model.calls, 0)

    async def test_shared_loop_reports_budget_failure_instead_of_calling_model(self):
        base = ScriptedModel([message("must not run")])
        model = cb.BudgetedModel(base, max_characters=1)
        result = await run_agent(model, "system", "required task", [], timeout=1)
        self.assertEqual(result.status, "error")
        self.assertEqual(base.requests, [])

    async def test_every_delegated_request_is_measured_and_audit_is_bounded(self):
        base = ScriptedModel([message("fixture") for _ in range(70)])
        model = cb.BudgetedModel(base, max_characters=500)
        messages = [{"role": "system", "content": "fixture"}, {"role": "user", "content": "任务"}]
        for _ in range(70):
            await model.complete(messages, [])
        self.assertEqual(model.calls, 70)
        self.assertEqual(len(model.reports), 64)
        self.assertTrue(all(report.after == cb.request_characters(**request) <= 500
                            for report, request in zip(model.reports, base.requests[-64:])))


class PlanningTests(unittest.IsolatedAsyncioTestCase):
    async def run_fixture(self, responses, *, tools=None, limits=None, verify_step=accepted, verify_goal=accepted):
        base = ScriptedModel(responses)
        result = await pl.run_plan_and_execute(GOAL, base, tools or [], verify_step=verify_step,
                                              verify_goal=verify_goal, limits=limits)
        return result, base

    async def test_demo_runs_files_replans_and_cleans_temporary_workspace(self):
        result = await pl.demo()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completed_steps"], ["write", "verify", "report"])
        self.assertEqual(result["replans"], 1)
        self.assertTrue(result["temporary_workspace_removed"])

    async def test_goal_verifier_can_reject_a_fully_executed_plan(self):
        async def rejected(*_):
            return False
        result, _ = await self.run_fixture([message(initial(step("one"))), message("fixture evidence"), keep()],
                                           verify_goal=rejected)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "goal_verification_failed")
        self.assertEqual(result.steps[0].status, "complete")

    async def test_step_verification_failure_never_runs_a_dependent_step(self):
        checked = []
        async def reject(step, outcome):
            checked.append(step.id)
            return False
        result, base = await self.run_fixture([message(initial(step("one"), step("two", ("one",)))),
                                               message("claims complete")], verify_step=reject)
        self.assertEqual(result.status, "failed")
        self.assertEqual([r.status for r in result.steps], ["failed", "pending"])
        self.assertEqual(checked, ["one"])
        self.assertEqual(len(base.requests), 2)

    async def test_failed_tool_cannot_be_hidden_by_a_final_success_sentence(self):
        def failed():
            raise OSError("synthetic tool failure")
        tool = Tool("fail", "Synthetic failing action", {"type": "object", "properties": {},
                                                        "required": [], "additionalProperties": False}, failed)
        call = {"role": "assistant", "content": None, "tool_calls": [{"id": "failure", "type": "function",
                "function": {"name": "fail", "arguments": "{}"}}]}
        result, _ = await self.run_fixture([message(initial(step("one", tools=("fail",)))), call,
                                           message("everything succeeded")], tools=[tool])
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "tool_error")
        self.assertEqual(result.steps[0].status, "failed")

    async def test_turn_limit_is_not_completed_or_checkpointed(self):
        calls = []
        tool = Tool("tick", "Count a real callback", {"type": "object", "properties": {},
                                                     "required": [], "additionalProperties": False},
                    lambda: calls.append(1) or {"count": len(calls)})
        call = {"role": "assistant", "content": None, "tool_calls": [{"id": "tick1", "type": "function",
                "function": {"name": "tick", "arguments": "{}"}}]}
        result, base = await self.run_fixture([message(initial(step("one", tools=("tick",)))), call],
            tools=[tool], limits=pl.PlanningLimits(max_turns_per_step=1))
        self.assertEqual(result.status, "limit")
        self.assertEqual(result.steps[0].status, "limit")
        self.assertEqual(calls, [1])
        self.assertEqual(len(base.requests), 2)

    async def test_tool_call_bound_stops_before_a_second_side_effect(self):
        executed = []
        tool = Tool("tick", "Count synthetic side effects", {"type": "object", "properties": {},
                    "required": [], "additionalProperties": False}, lambda: executed.append(1) or {})
        calls = [{"id": name, "type": "function", "function": {"name": "tick", "arguments": "{}"}}
                 for name in ("first", "second")]
        result, base = await self.run_fixture([
            message(initial(step("one", tools=("tick",)))),
            {"role": "assistant", "content": None, "tool_calls": calls}], tools=[tool],
            limits=pl.PlanningLimits(max_tool_calls_per_step=1))
        self.assertEqual((result.status, result.steps[0].status), ("limit", "limit"))
        self.assertEqual(executed, [1])
        self.assertEqual(len(base.requests), 2)

    async def test_planner_timeout_is_covered_by_the_overall_deadline(self):
        stopped = asyncio.Event()
        class Hanging:
            async def complete(self, messages, tools):
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()
        result = await pl.run_plan_and_execute(GOAL, Hanging(), [], verify_step=accepted, verify_goal=accepted,
                                               limits=pl.PlanningLimits(timeout=0.03))
        self.assertEqual((result.status, result.phase, result.attempts), ("timeout", "planning", 0))
        self.assertTrue(stopped.is_set())

    async def test_step_timeout_does_not_mark_complete_or_start_checkpoint(self):
        calls = 0
        stopped = asyncio.Event()
        class HangingStep:
            async def complete(self, messages, tools):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return message(initial(step("one"), step("two", ("one",))))
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()
        result = await pl.run_plan_and_execute(GOAL, HangingStep(), [], verify_step=accepted, verify_goal=accepted,
            limits=pl.PlanningLimits(timeout=1.0, step_timeout=0.03))
        self.assertEqual(result.status, "timeout")
        self.assertEqual([r.status for r in result.steps], ["timeout", "pending"])
        self.assertEqual(calls, 2)
        self.assertTrue(stopped.is_set())

    async def test_overall_deadline_includes_checkpoint_calls(self):
        class HangingCheckpoint:
            def __init__(self):
                self.count = 0
            async def complete(self, messages, tools):
                self.count += 1
                if self.count == 1:
                    return message(initial(step("one")))
                if self.count == 2:
                    return message("fixture evidence")
                await asyncio.Event().wait()
        model = HangingCheckpoint()
        result = await pl.run_plan_and_execute(GOAL, model, [], verify_step=accepted, verify_goal=accepted,
                                               limits=pl.PlanningLimits(timeout=0.03))
        self.assertEqual((result.status, result.phase), ("timeout", "checkpoint"))
        self.assertEqual(result.steps[0].status, "complete")
        self.assertEqual(model.count, 3)

    async def test_overall_deadline_also_covers_async_verifiers(self):
        entered = asyncio.Event()
        async def never(*_):
            entered.set()
            await asyncio.Event().wait()
        result, _ = await self.run_fixture([message(initial(step("one"))), message("fixture")],
            limits=pl.PlanningLimits(timeout=0.03, step_timeout=1), verify_step=never)
        self.assertTrue(entered.is_set())
        self.assertEqual((result.status, result.phase), ("timeout", "verification"))
        self.assertEqual(result.steps[0].status, "timeout")

    async def test_external_cancellation_propagates_and_does_not_reach_verification(self):
        started = asyncio.Event()
        verified = []
        class Blocked:
            async def complete(self, messages, tools):
                started.set()
                await asyncio.Event().wait()
        async def verifier(*_):
            verified.append(1)
            return True
        task = asyncio.create_task(pl.run_plan_and_execute(GOAL, Blocked(), [], verify_step=verifier,
                                                          verify_goal=verifier))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(verified, [])

    async def test_replan_limit_stops_instead_of_rewriting_forever(self):
        result, base = await self.run_fixture([message(initial(step("one"))), message("fixture"),
                                               replan(step("two", ("one",)))],
                                              limits=pl.PlanningLimits(max_replans=0))
        self.assertEqual((result.status, result.reason, result.replans), ("limit", "replan_limit", 0))
        self.assertEqual([r.step.id for r in result.steps], ["one"])
        self.assertEqual(len(base.requests), 3)

    async def test_step_bound_counts_attempts_across_accepted_replans(self):
        responses = [message(initial(step("one"))), message("fixture1"), replan(step("two", ("one",))),
                     message("fixture2"), replan(step("three", ("two",)))]
        result, base = await self.run_fixture(responses, limits=pl.PlanningLimits(max_steps=2, max_replans=3))
        self.assertEqual((result.status, result.reason, result.attempts), ("limit", "step_limit", 2))
        self.assertEqual(result.replans, 2)
        self.assertEqual([r.status for r in result.steps], ["complete", "complete", "pending"])
        self.assertEqual(len(base.requests), 5)

    async def test_replan_cannot_replace_completed_evidence(self):
        result, _ = await self.run_fixture([message(initial(step("one"))), message("checked original evidence"),
                                            replan(step("one"))])
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.steps[0].summary, "checked original evidence")
        self.assertEqual(result.steps[0].status, "complete")
        self.assertEqual(result.replans, 0)

    async def test_dependency_cycles_duplicates_unknown_tools_and_model_status_are_rejected(self):
        cases = [initial(step("one", ("two",)), step("two", ("one",))),
                 initial(step("one"), step("one")), initial(step("one", ("missing",))),
                 initial(step("one", tools=("not_available",)))]
        forged = initial(step("one")); forged["steps"][0]["status"] = "complete"; cases.append(forged)
        for data in cases:
            with self.subTest(data=data):
                result, base = await self.run_fixture([message(data)])
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.attempts, 0)
                self.assertEqual(len(base.requests), 1)

    async def test_empty_or_malformed_plan_and_fake_early_finish_are_rejected(self):
        for response in [message("not-json"), message(initial()), message({"goal": "changed"})]:
            with self.subTest(response=response):
                result, _ = await self.run_fixture([response])
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.attempts, 0)
        result, _ = await self.run_fixture([message(initial(step("one"), step("two", ("one",)))),
                                            message("fixture"), message({"can_finish_early": True})])
        self.assertEqual(result.status, "failed")
        self.assertEqual([r.status for r in result.steps], ["complete", "pending"])

    async def test_model_failure_and_non_boolean_verifier_are_structured_failures(self):
        class Failing:
            async def complete(self, messages, tools):
                raise RuntimeError("synthetic provider failure")
        result = await pl.run_plan_and_execute(GOAL, Failing(), [], verify_step=accepted, verify_goal=accepted)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "operation_error:RuntimeError")
        result, _ = await self.run_fixture([message(initial(step("one"))), message("fixture")],
                                          verify_step=lambda *_: "success")
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.steps[0].status, "failed")

    async def test_provider_timeout_is_not_mislabelled_as_expired_overall_deadline(self):
        class ProviderTimeout:
            async def complete(self, messages, tools):
                raise TimeoutError("synthetic provider timeout")
        result = await pl.run_plan_and_execute(GOAL, ProviderTimeout(), [],
                                               verify_step=accepted, verify_goal=accepted)
        self.assertEqual((result.status, result.reason), ("timeout", "operation_timeout"))
        async def verifier_timeout(*_):
            raise TimeoutError("synthetic verifier timeout")
        result, _ = await self.run_fixture([message(initial(step("one"))), message("fixture")],
                                           verify_step=verifier_timeout)
        self.assertEqual((result.status, result.reason), ("timeout", "step_timeout"))
        self.assertEqual(result.steps[0].status, "timeout")

    async def test_planning_request_budget_is_checked_before_model(self):
        result, base = await self.run_fixture([message("must not run")],
                                              limits=pl.PlanningLimits(max_request_characters=1))
        self.assertEqual((result.status, result.reason), ("failed", "context_budget"))
        self.assertEqual(base.requests, [])


if __name__ == "__main__":
    unittest.main()
