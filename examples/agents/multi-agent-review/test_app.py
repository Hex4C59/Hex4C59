import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_runtime import ScriptedModel
from app import (MAX_DIFF_BYTES, ROLES, fixture_model, load_diff_file, load_git_diff,
                 parse_diff, render_report, review_diff, validate_report)

FIXTURE = Path(__file__).parent / "fixtures" / "demo.diff"


class DiffTests(unittest.IsolatedAsyncioTestCase):
    def test_file_and_line_evidence_validation(self):
        diff = load_diff_file(FIXTURE)
        self.assertEqual(diff.additions["pricing.py"][2], "    return price - percent")
        payload = json.loads(fixture_model("logic").responses[-1]["content"])
        self.assertEqual(len(validate_report(json.dumps(payload), diff)["findings"]), 1)
        for mutation in ({"line": 1}, {"path": "missing.py"}, {"evidence": "invented line"},
                         {"severity": "critical"}, {"line": True}):
            invalid = copy.deepcopy(payload)
            invalid["findings"][0].update(mutation)
            with self.assertRaises(Exception):
                validate_report(json.dumps(invalid), diff)

    def test_truncated_large_binary_and_traversal_diffs_fail(self):
        text = FIXTURE.read_text()
        for invalid in (text.replace("+1,2", "+1,3"), text.replace("b/pricing.py\n@@", "b/../pricing.py\n@@"),
                        "Binary files a and b differ", "x" * (MAX_DIFF_BYTES + 1),
                        text.replace("@@ -1,2", "@@@ -1,2")):
            with self.assertRaises(ValueError):
                parse_diff(invalid, "test")

    async def test_git_output_limit_and_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            file = root / "large.txt"
            file.write_text("old\n")
            subprocess.run(["git", "add", "large.txt"], cwd=root, check=True)
            file.write_text("x" * (MAX_DIFF_BYTES + 100))
            with self.assertRaisesRegex(ValueError, "Git output exceeds"):
                await load_git_diff(root)
            with self.assertRaises(TimeoutError):
                await load_git_diff(root, timeout=0)

    async def test_actual_git_diff_worktree_staged_and_nonrepo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            file = root / "pricing.py"
            file.write_text("def discounted(price, percent):\n    return price * (1 - percent / 100)\n")
            subprocess.run(["git", "add", "pricing.py"], cwd=root, check=True)
            file.write_text("def discounted(price, percent):\n    return price - percent\n")
            diff = await load_git_diff(root)
            self.assertEqual(diff.additions["pricing.py"][2], "    return price - percent")
            subprocess.run(["git", "add", "pricing.py"], cwd=root, check=True)
            staged = await load_git_diff(root, staged=True)
            self.assertEqual(staged.additions["pricing.py"][2], diff.additions["pricing.py"][2])
            self.assertEqual((await load_git_diff(root)).additions, {})
            batch = await review_diff(staged, fixture_model)
            self.assertFalse(batch.partial)
            self.assertEqual(len(batch.results[0].findings), 1)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "git diff exited"):
                await load_git_diff(Path(directory))


class ReviewerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.diff = load_diff_file(FIXTURE)

    async def test_real_overlap_is_bounded_and_models_are_closed(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        active = peak = 0
        closed = []
        models = []
        class Model:
            def __init__(self, role):
                self.role = role
                self.inner = fixture_model(role)
            async def complete(self, messages, tools):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                if active == 2:
                    entered.set()
                try:
                    await release.wait()
                    return await self.inner.complete(messages, tools)
                finally:
                    active -= 1
            async def aclose(self):
                closed.append(self.role)
        def factory(role):
            model = Model(role)
            models.append(model)
            return model
        task = asyncio.create_task(review_diff(self.diff, factory, concurrency=2))
        await asyncio.wait_for(entered.wait(), 2)
        self.assertEqual(active, 2)
        release.set()
        batch = await task
        self.assertEqual(peak, 2)
        self.assertFalse(batch.partial)
        self.assertEqual(sorted(closed), sorted(ROLES))
        self.assertEqual(len({id(m.inner.requests[0]["messages"]) for m in models}), 3)

    async def test_invalid_and_error_preserve_successful_partial_findings(self):
        def factory(role):
            if role == "security":
                return ScriptedModel([{"role": "assistant", "content": "not JSON"}])
            if role == "performance":
                return ScriptedModel([])
            return fixture_model(role)
        batch = await review_diff(self.diff, factory)
        self.assertTrue(batch.partial)
        self.assertEqual([r.status for r in batch.results], ["complete", "invalid", "error"])
        rendered = render_report(batch, "local test", "fixture")
        self.assertIn("PARTIAL", rendered)
        self.assertIn("pricing", rendered)
        self.assertIn("No project tests were executed", rendered)
        self.assertIn("security: invalid", rendered)

    async def test_timeout_and_cancellation_are_not_empty_success(self):
        gate = asyncio.Event()
        closed = []
        class SlowModel:
            def __init__(self, role):
                self.role = role
            async def complete(self, messages, tools):
                gate.set()
                await asyncio.sleep(60)
            async def aclose(self):
                closed.append(self.role)
        batch = await review_diff(self.diff, lambda role: SlowModel(role), timeout=.02)
        self.assertTrue(batch.partial)
        self.assertTrue(all(r.status == "timeout" for r in batch.results))
        self.assertEqual(sorted(closed), sorted(ROLES))
        gate.clear()
        closed.clear()
        task = asyncio.create_task(review_diff(self.diff, lambda role: SlowModel(role), concurrency=1))
        await asyncio.wait_for(gate.wait(), 2)
        task.cancel()
        batch = await task
        self.assertTrue(batch.cancelled)
        self.assertEqual([r.status for r in batch.results], ["cancelled"] * 3)
        self.assertEqual(closed, ["logic"])

    async def test_cancellation_keeps_already_completed_result(self):
        done = asyncio.Event()
        class SlowModel:
            async def complete(self, messages, tools):
                await asyncio.sleep(60)
        def emit(role, event):
            if role == "logic" and event["event"] == "review.end":
                done.set()
        task = asyncio.create_task(review_diff(self.diff,
            lambda role: fixture_model(role) if role == "logic" else SlowModel(), emit=emit))
        await asyncio.wait_for(done.wait(), 2)
        task.cancel()
        batch = await task
        self.assertEqual(batch.results[0].status, "complete")
        self.assertEqual(len(batch.results[0].findings), 1)
        self.assertTrue(batch.partial)


class EntrypointTests(unittest.TestCase):
    def test_live_without_credentials_has_no_fixture_fallback(self):
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_MODEL", None)
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("app.py")),
                                "--live", "--diff", str(FIXTURE)], env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENAI_API_KEY", result.stderr)
        self.assertNotIn("Mode: fixture", result.stdout)

    def test_default_cli_and_custom_file_are_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            app = str(Path(__file__).with_name("app.py"))
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            result = subprocess.run([sys.executable, "-B", app], cwd=directory, env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Mode: fixture", result.stdout)
            self.assertIn("logic: complete", result.stdout)
            self.assertIn("No project tests were executed", result.stdout)
            custom = subprocess.run([sys.executable, "-B", app, "--diff", str(FIXTURE)],
                                    cwd=directory, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(custom.returncode, 0, custom.stderr)
            self.assertIn("do not analyze custom code", custom.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
