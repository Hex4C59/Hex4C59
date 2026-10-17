"""Offline integration: real corpus files and the shared async tool loop."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_runtime import ScriptedModel
import app
from fixture_model import CorpusFixtureModel
from pipeline import Evidence, Limits, mechanical_check, render_report, run_research
from sources import CorpusProvider, MAX_DOCUMENT_BYTES, MAX_MANIFEST_BYTES, strict_json

HERE = Path(__file__).parent
BUNDLED = (HERE / "agent_runtime.py").is_file()
ROOT = HERE if BUNDLED else HERE.parents[2]
COMMON = HERE if BUNDLED else HERE.parent / "common"
PACKAGE = "app" if BUNDLED else "examples.agents.research"
TASK = "整理本地资料的记录与复核要求。"


def corpus_at(directory, content="这是用户本地语料中的明确要求：每次修订都要重新检查。"):
    (directory / "document.txt").write_text(content, encoding="utf-8")
    manifest = directory / "corpus.json"
    manifest.write_text(json.dumps({"label": "用户本地测试语料", "documents": [
        {"id": "Local1", "title": "用户提供的记录", "file": "document.txt"}]}, ensure_ascii=False), encoding="utf-8")
    return manifest


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    def provider(self):
        return CorpusProvider(app.FIXTURE_CORPUS)

    async def test_full_fetch_note_citation_revision_recheck_and_shared_fixture_replay(self):
        model = CorpusFixtureModel()
        result = await run_research(TASK, model, self.provider())
        self.assertEqual(result.status, "complete")
        self.assertEqual([c["passed"] for c in result.checks], [False, True])
        self.assertIn("unknown_citation:N999", result.checks[0]["mechanical_issues"])
        self.assertEqual(len(result.notes), 2)
        for note in result.notes:
            source = next(s for s in result.sources if s["source_id"] == note["source_id"])
            self.assertEqual(source["text"][note["start"]:note["end"]], note["quote"])
            self.assertEqual(hashlib.sha256(source["text"].encode()).hexdigest(), note["source_sha256"])
            fetched = next(i for i, e in enumerate(result.events) if e["event"] == "fetch" and e["source_id"] == note["source_id"])
            noted = next(i for i, e in enumerate(result.events) if e["event"] == "note" and e["note_id"] == note["id"])
            self.assertLess(fetched, noted)
        markdown = render_report(result)
        self.assertIn("[N1](#note-n1)", markdown)
        self.assertIn("SHA-256", markdown)
        self.assertNotIn("N999", markdown)
        synth = [r for r in model.requests if r["messages"][0]["content"].startswith("STAGE: synthesize")]
        payload = strict_json(synth[1]["messages"][1]["content"])
        self.assertIsNotNone(payload["previous"])
        self.assertIn("unknown_citation:N999", payload["feedback"])
        replay = ScriptedModel(model.responses)
        rerun = await run_research(TASK, replay, self.provider())
        self.assertEqual(rerun.status, "complete")
        self.assertEqual(next(r for r in replay.requests if r["tools"])["tools"][0]["type"], "function")

    async def test_first_draft_success(self):
        result = await run_research(TASK, CorpusFixtureModel(bad_first=False), self.provider(), limits=Limits(max_revisions=0))
        self.assertEqual(result.status, "complete")
        self.assertEqual(len(result.checks), 1)

    async def test_revision_limits_check_every_draft_and_never_publish_failed_one(self):
        for count in (0, 2):
            with self.subTest(revisions=count):
                result = await run_research(TASK, CorpusFixtureModel(always_bad=True), self.provider(), limits=Limits(max_revisions=count))
                self.assertEqual(result.status, "quality_failed")
                self.assertEqual(len(result.checks), count + 1)
                self.assertIsNone(result.report)
                self.assertNotIn("本地语料研究记录", render_report(result))

    async def test_actual_empty_search_does_not_become_completed_research(self):
        result = await run_research(TASK, CorpusFixtureModel(query_override="zzzz_no_matching_token_4829"), self.provider())
        self.assertEqual(result.status, "error")
        self.assertIn("no_evidence:Q1", result.errors)
        self.assertIn({"event": "search", "hits": 0}, result.events)
        self.assertEqual(result.notes, [])

    async def test_real_source_read_error_reaches_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            provider = CorpusProvider(corpus_at(directory))
            (directory / "document.txt").unlink()
            model = CorpusFixtureModel()
            result = await run_research(TASK, model, provider)
            self.assertEqual(result.status, "error")
            messages = [m for request in model.requests for m in request["messages"] if m["role"] == "tool"]
            self.assertTrue(any(strict_json(m["content"]).get("error_type") == "FileNotFoundError" for m in messages))
            self.assertIsNone(result.report)

    async def test_fabricated_claim_with_real_citation_fails_whole_pipeline(self):
        class FabricatingModel(CorpusFixtureModel):
            def respond(self, messages):
                response = super().respond(messages)
                if messages[0]["content"].startswith("STAGE: synthesize"):
                    draft = strict_json(response["content"])
                    draft["claims"][0]["text"] = "系统保证所有研究结论永远正确且来源绝对独立。"
                    response["content"] = json.dumps(draft, ensure_ascii=False)
                return response
        result = await run_research(TASK, FabricatingModel(bad_first=False), self.provider(), limits=Limits(max_revisions=0))
        self.assertEqual(result.status, "quality_failed")
        self.assertIn("claim_not_in_cited_note:N1", result.checks[0]["mechanical_issues"])
        self.assertIsNone(result.report)

    async def test_source_request_timeout_is_a_tool_error_not_new_evidence(self):
        class SlowProvider(CorpusProvider):
            async def search(self, query, limit=5):
                await asyncio.sleep(1)
                return await super().search(query, limit)
        result = await run_research(TASK, CorpusFixtureModel(), SlowProvider(app.FIXTURE_CORPUS),
                                    limits=Limits(request_timeout=0.01))
        self.assertEqual(result.status, "error")
        self.assertEqual(result.notes, [])
        self.assertIn({"event": "tool_error", "stage": "research", "error_type": "TimeoutError"}, result.events)

    async def test_corrupt_fetched_checksum_is_rejected(self):
        class CorruptProvider(CorpusProvider):
            async def fetch(self, source_id):
                return replace(await super().fetch(source_id), sha256="0" * 64)
        result = await run_research(TASK, CorpusFixtureModel(), CorruptProvider(app.FIXTURE_CORPUS))
        self.assertEqual(result.status, "error")
        self.assertEqual(result.notes, [])
        self.assertIsNone(result.report)

    async def test_turn_and_tool_limits_fail_closed(self):
        for limits in (Limits(research_turns=1), Limits(tool_calls_per_question=1)):
            result = await run_research(TASK, CorpusFixtureModel(), self.provider(), limits=limits)
            self.assertEqual(result.status, "limit")
            self.assertIsNone(result.report)

    async def test_model_review_cannot_override_mechanical_failure(self):
        class DishonestReview(CorpusFixtureModel):
            def respond(self, messages):
                if messages[0]["content"].startswith("STAGE: review"):
                    return {"role": "assistant", "content": '{"passed":true,"issues":[]}'}
                return super().respond(messages)
        result = await run_research(TASK, DishonestReview(always_bad=True), self.provider(), limits=Limits(max_revisions=0))
        self.assertEqual(result.status, "quality_failed")
        self.assertFalse(result.checks[0]["passed"])

    async def test_request_timeout_cancels_awaited_model(self):
        class SlowModel:
            cancelled = False
            async def complete(self, messages, tools):
                try:
                    await asyncio.sleep(2)
                finally:
                    self.cancelled = True
        model = SlowModel()
        result = await run_research(TASK, model, self.provider(), limits=Limits(request_timeout=0.01, total_timeout=1))
        self.assertEqual(result.status, "timeout")
        self.assertTrue(model.cancelled)
        self.assertIsNone(result.report)

    async def test_total_deadline_spans_stages_not_just_one_request(self):
        class DelayedFixture(CorpusFixtureModel):
            async def complete(self, messages, tools):
                await asyncio.sleep(0.025)
                return await super().complete(messages, tools)
        started = time.monotonic()
        result = await run_research(TASK, DelayedFixture(), self.provider(), limits=Limits(total_timeout=0.09, request_timeout=0.5))
        self.assertEqual(result.status, "timeout")
        self.assertTrue(any("total_deadline_reached" in error for error in result.errors))
        self.assertLess(time.monotonic() - started, 1)
        self.assertIsNone(result.report)

    async def test_caller_cancellation_propagates(self):
        started = asyncio.Event()
        class WaitingModel:
            async def complete(self, messages, tools):
                started.set()
                await asyncio.sleep(2)
        pending = asyncio.create_task(run_research(TASK, WaitingModel(), self.provider()))
        await started.wait()
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending

    async def test_model_errors_bad_json_and_oversized_responses(self):
        for model in (ScriptedModel([]), ScriptedModel([{"role": "assistant", "content": "not JSON"}]),
                      ScriptedModel([{"role": "assistant", "content": "x" * 32_001}])):
            result = await run_research(TASK, model, self.provider())
            self.assertEqual(result.status, "error")
            self.assertIsNone(result.report)

    async def test_live_client_closed_on_failure(self):
        class CloseableFixture(CorpusFixtureModel):
            closed = False
            async def aclose(self):
                self.closed = True
        model = CloseableFixture(always_bad=True)
        args = app.parser().parse_args(["--live", "--corpus", str(app.FIXTURE_CORPUS), "--max-revisions", "0"])
        with patch.object(app, "model_from_env", return_value=model), redirect_stdout(io.StringIO()):
            code = await app.async_main(args)
        self.assertEqual(code, 1)
        self.assertTrue(model.closed)


class EvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.evidence = Evidence(CorpusProvider(app.FIXTURE_CORPUS), Limits(), [])

    async def test_notes_require_fetch_and_exact_quote(self):
        with self.assertRaisesRegex(ValueError, "Fetch"):
            self.evidence.save_note("Q1", "S1", "这是一个没有读取来源就写入的虚构事实。")
        await self.evidence.fetch("S1")
        with self.assertRaisesRegex(ValueError, "absent"):
            self.evidence.save_note("Q1", "S1", "这是一个原文没有支持的虚构事实。")

    async def test_unsubstantiated_citations_claims_and_tampered_provenance(self):
        source = await self.evidence.fetch("S1")
        note = self.evidence.save_note("Q1", "S1", source["text"].splitlines()[0])
        plan = {"questions": [{"id": "Q1"}]}
        valid = {"title": "证据", "claims": [{"question_id": "Q1", "text": note["quote"], "note_ids": ["N1"]}], "limitations": ["仅本地语料。"]}
        self.assertEqual(mechanical_check(plan, valid, self.evidence), [])
        for field, value, expected in (("text", "系统保证所有研究结论永远正确且来源绝对独立。", "claim_not_in_cited_note:N1"),
                                       ("note_ids", ["N404"], "unknown_citation:N404"),
                                       ("question_id", "Q2", "citation_question_mismatch:N1")):
            draft = deepcopy(valid)
            draft["claims"][0][field] = value
            self.assertIn(expected, mechanical_check(plan, draft, self.evidence))
        self.evidence.notes[0] = replace(self.evidence.notes[0], source_sha256="0" * 64)
        self.assertIn("invalid_note_provenance:N1", mechanical_check(plan, valid, self.evidence))

    async def test_source_count_limit(self):
        self.evidence.limits = Limits(max_sources=1)
        await self.evidence.fetch("S1")
        with self.assertRaisesRegex(ValueError, "limit"):
            await self.evidence.fetch("S2")

    async def test_private_urls_are_not_fetch_targets(self):
        with patch("socket.create_connection", side_effect=AssertionError("No source networking")):
            for url in ("http://127.0.0.1/private", "http://169.254.169.254/", "http://[::1]/", "file:///etc/passwd"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    await self.evidence.fetch(url)
            self.assertEqual((await self.evidence.fetch("S1"))["source_id"], "S1")


class CorpusTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_empty_and_oversized_source_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            provider = CorpusProvider(corpus_at(directory))
            for raw in (b"", b"bad\x00data", b"\xff\xfe", b"x" * (MAX_DOCUMENT_BYTES + 1)):
                with self.subTest(raw_length=len(raw)):
                    (directory / "document.txt").write_bytes(raw)
                    with self.assertRaises((ValueError, UnicodeError)):
                        await provider.fetch("Local1")

    async def test_malformed_manifest_duplicates_and_escape_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = corpus_at(directory)
            original = json.loads(manifest.read_text())
            variants = [{}, {"label": "x", "documents": []}, {"label": "x", "documents": [None]},
                        {"label": "x", "documents": original["documents"] * 2}]
            for field, value in (("file", "../escape.txt"), ("file", "/etc/passwd"), ("title", 42), ("id", "bad id"),
                                 ("url", "file:///etc/passwd"), ("url", "https://user:password@example.invalid/"), ("published_at", "not-a-date")):
                data = deepcopy(original)
                data["documents"][0][field] = value
                variants.append(data)
            for data in variants:
                with self.subTest(data=data):
                    manifest.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises((ValueError, TypeError)):
                        CorpusProvider(manifest)
            for raw in ("not-json", '{"label":"a","label":"b","documents":[]}', "x" * (MAX_MANIFEST_BYTES + 1)):
                manifest.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    CorpusProvider(manifest)

    async def test_source_markup_is_literal_in_rendered_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = corpus_at(directory, "<script>alert('x')</script> 这是一段供测试引用的本地文本。")
            result = await run_research(TASK, CorpusFixtureModel(), CorpusProvider(manifest))
            self.assertEqual(result.status, "complete")
            rendered = render_report(result)
            self.assertNotIn("<script>", rendered)
            self.assertIn("&lt;script&gt;", rendered)

    async def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = corpus_at(directory)
            (directory / "alias.txt").symlink_to(directory / "document.txt")
            data = json.loads(manifest.read_text())
            data["documents"][0]["file"] = "alias.txt"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                CorpusProvider(manifest)


class CLITests(unittest.TestCase):
    def environment(self):
        env = dict(os.environ, PYTHONPATH=str(COMMON), PYTHONDONTWRITEBYTECODE="1")
        if BUNDLED:
            env.pop("PYTHONPATH", None)
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_MODEL", None)
        return env

    def test_default_script_and_package_entrypoints(self):
        with tempfile.TemporaryDirectory() as temporary:
            for command, cwd in (([sys.executable, str(HERE / "app.py")], temporary),
                                 ([sys.executable, "-m", PACKAGE], ROOT)):
                run = subprocess.run(command, cwd=cwd, env=self.environment(), text=True, capture_output=True, timeout=15)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn("mode=fixture", run.stdout)
                self.assertIn("check revision=1 passed=true", run.stdout)
                self.assertIn("citations=N1:S1,N2:S2", run.stdout)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_custom_corpus_persists_actual_notes_in_explicit_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = corpus_at(directory)
            workspace = directory / "output"
            run = subprocess.run([sys.executable, str(HERE / "app.py"), "--corpus", str(manifest), "--workspace", str(workspace),
                                  "--task", "整理用户本地记录。"], cwd=directory, env=self.environment(), text=True, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(next(workspace.glob("run-*/result.json")).read_text())
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["notes"][0]["quote"], (directory / "document.txt").read_text())
            self.assertEqual(result["sources"][0]["file"], "document.txt")
            self.assertTrue(result["checks"][-1]["passed"])

    def test_live_requires_corpus_and_credentials(self):
        for args in (["--live"], ["--live", "--corpus", str(app.FIXTURE_CORPUS)]):
            run = subprocess.run([sys.executable, str(HERE / "app.py"), *args], env=self.environment(), text=True, capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertIn("configuration_error", run.stderr)
            self.assertNotIn("status=complete", run.stdout)

    def test_invalid_timeouts_rejected(self):
        for value in ("nan", "inf", "0", "-1"):
            with self.subTest(value=value), patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                app.parser().parse_args(["--timeout", value])


if __name__ == "__main__":
    unittest.main()
