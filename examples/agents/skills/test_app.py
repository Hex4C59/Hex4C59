"""Offline integration tests exercise the real runtime, registered tools and files."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_runtime import ScriptedModel
import app


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="skills-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        app.initialize_samples(self.root)
        self.workspace = app.Workspace(self.root)
        self.loader = app.SkillLoader(self.workspace)

    def test_match_rules_explicit_names_and_negative_case(self):
        self.assertEqual([s.name for s in self.loader.select("a BLOG DRAFT please")], ["write-blog"])
        self.assertEqual([s.name for s in self.loader.select("写博客，并解释代码")], ["explain-code", "write-blog"])
        self.assertEqual(self.loader.select("明天天气怎样"), [])
        self.assertEqual(self.loader.select("写博客", []), [])
        self.assertEqual([s.name for s in self.loader.select("unrelated", ["write-blog"])], ["write-blog"])
        with self.assertRaisesRegex(ValueError, "Unknown Skill"):
            self.loader.select("写博客", ["missing"])

    def test_scan_refreshes_without_accumulating_duplicates(self):
        self.loader.scan()
        self.assertEqual(sorted(self.loader.skills), ["explain-code", "write-blog"])
        path = self.root / "skills/explain-code/SKILL.md"
        path.unlink()
        self.loader.scan()
        self.assertNotIn("explain-code", self.loader.skills)

    def test_yaml_folded_description_and_final_line_without_newline(self):
        text = self.workspace.read("skills/write-blog/SKILL.md").rstrip()
        skill = app.parse_skill(text, "skills/write-blog/SKILL.md")
        self.assertIn("Chinese teaching draft", skill.description)
        self.assertIn("blog draft", skill.triggers)
        self.assertTrue(skill.content.endswith("发布规范。"))

    def test_malformed_or_duplicate_skill_metadata_is_rejected(self):
        original = self.workspace.read("skills/write-blog/SKILL.md")
        variants = [original.replace("name: write-blog", "name: write-blog\nname: other"),
                    original.replace("triggers:", "unexpected:"),
                    original.replace("  - 写博客\n  - 写一篇\n  - blog draft", ""),
                    original.replace("---", "+++", 1)]
        for invalid in variants:
            with self.subTest(invalid=invalid[:60]):
                with self.assertRaises((ValueError, app.yaml.YAMLError)):
                    app.parse_skill(invalid, "skills/write-blog/SKILL.md")

    def test_declared_reference_is_read_only_for_selected_skill(self):
        reference = "skills/write-blog/references/structure.md"
        self.assertNotIn(reference, self.workspace.reads)
        self.loader.context(self.loader.select("解释代码"))
        self.assertNotIn(reference, self.workspace.reads)
        context = self.loader.context(self.loader.select("写博客"))
        self.assertIn("draft 必须为 true", context)
        self.assertIn(reference, self.workspace.reads)

    def test_missing_or_symlink_reference_is_rejected(self):
        reference = self.root / "skills/write-blog/references/structure.md"
        reference.unlink()
        with self.assertRaises(FileNotFoundError):
            self.loader.context(self.loader.select("写博客"))
        with tempfile.TemporaryDirectory(prefix="skills-outside-") as outside:
            target = Path(outside) / "note.md"
            target.write_text("outside", encoding="utf-8")
            reference.symlink_to(target)
            with self.assertRaises(ValueError):
                self.loader.context(self.loader.select("写博客"))

    def test_read_and_write_reject_absolute_traversal_and_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="skills-outside-") as outside:
            external = Path(outside) / "keep.md"
            external.write_text("keep", encoding="utf-8")
            (self.root / "drafts/link.md").symlink_to(external)
            for relative in (str(external), "../keep.md", "drafts/../../keep.md", "drafts/link.md"):
                with self.subTest(path=relative):
                    with self.assertRaises(ValueError):
                        self.workspace.read(relative)
                    with self.assertRaises(ValueError):
                        self.workspace.write_file(relative, "overwrite")
            self.assertEqual(external.read_text(encoding="utf-8"), "keep")

    def test_generic_writer_cannot_persist_skills_or_rewrite_proposals(self):
        for relative in ("skills/new/SKILL.md", "inputs/skill-proposal.json", "app.py"):
            with self.assertRaises(PermissionError):
                self.workspace.write_file(relative, "blocked")

    def test_overwrite_needs_one_use_approval_bound_to_existing_bytes(self):
        self.workspace.write_file("drafts/article.md", "first")
        with self.assertRaises(PermissionError):
            self.workspace.write_file("drafts/article.md", "unapproved")
        self.workspace.approve_overwrite("drafts/article.md")
        self.workspace.write_file("drafts/article.md", "approved")
        with self.assertRaises(PermissionError):
            self.workspace.write_file("drafts/article.md", "again")
        self.workspace.approve_overwrite("drafts/article.md")
        (self.root / "drafts/article.md").write_text("changed after review", encoding="utf-8")
        with self.assertRaises(PermissionError):
            self.workspace.write_file("drafts/article.md", "stale approval")

    def test_large_file_read_and_write_are_bounded(self):
        (self.root / "inputs/large.md").write_text("x" * (app.MAX_BYTES + 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.workspace.read("inputs/large.md")
        with self.assertRaises(ValueError):
            self.workspace.write_file("drafts/large.md", "x" * (app.MAX_BYTES + 1))

    def test_exact_proposal_approval_is_required_and_creation_rescans(self):
        proposal = json.loads(self.workspace.read("inputs/skill-proposal.json"))
        with self.assertRaises(PermissionError):
            self.loader.create_skill(**proposal)
        self.assertFalse((self.root / "skills/explain-cache").exists())
        self.workspace.approve_proposal("inputs/skill-proposal.json")
        changed = dict(proposal, content=proposal["content"] + "\n未批准的规则。")
        with self.assertRaises(PermissionError):
            self.loader.create_skill(**changed)
        result = self.loader.create_skill(**proposal)
        self.assertEqual(result["scan"], 2)
        self.assertEqual([s.name for s in self.loader.select("缓存检查")], ["explain-cache"])
        self.assertIn("不编造性能数字", self.loader.context(self.loader.select("缓存检查")))
        self.assertIn("explain-cache", app.SkillLoader(self.workspace).skills)
        with self.assertRaises(PermissionError):
            self.loader.create_skill(**proposal)

    def test_approved_create_never_overwrites_an_existing_skill(self):
        proposal = json.loads(self.workspace.read("inputs/skill-proposal.json"))
        self.workspace.approve_proposal("inputs/skill-proposal.json")
        destination = self.root / "skills/explain-cache"
        destination.mkdir()
        sentinel = destination / "SKILL.md"
        sentinel.write_text("user work", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.loader.create_skill(**proposal)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "user work")

    def test_artifact_checks_reject_invalid_form_and_missing_content(self):
        good = app.sample_article()
        variants = {
            "missing title": good.replace('title = "字典缓存示例"\n', ""),
            "invalid TOML": good.replace('draft = true', 'draft = ???'),
            "wrong tags": good.replace('tags = ["Python"]', 'tags = "Python"'),
            "published": good.replace('draft = true', 'draft = false'),
            "wrong topic": good.replace("缓存", "另一个主题"),
            "missing heading": good.replace("## 示例", "## 其他"),
            "fake heading in code": good.replace("## 先给结论", "## 其他").replace("cache = {}", "# ## 先给结论\ncache = {}"),
            "missing reference": good.replace("[合成任务资料](../inputs/source-notes.md)", "没有引用"),
            "missing target": good.replace("source-notes.md", "missing.md"),
            "invalid URL": good.replace("../inputs/source-notes.md", "javascript:alert"),
            "malformed URL": good.replace("../inputs/source-notes.md", "https://[broken"),
            "invalid Python": good.replace("cache = {}", "cache = ["),
            "comments only": good.replace('cache = {}\nkey = "demo"\nif key not in cache:\n    cache[key] = 2 + 3\nprint(cache[key])', "# no statements"),
            "unclosed fence": good.replace("print(cache[key])\n```", "print(cache[key])"),
            "unlabelled code": good.replace("```python", "```"),
        }
        for number, (name, content) in enumerate(variants.items()):
            with self.subTest(name=name):
                path = f"drafts/bad-{number}.md"
                self.workspace.write_file(path, content)
                check = app.check_artifact(self.workspace, path, "缓存")
                self.assertTrue(check.artifact_read)
                self.assertFalse(check.ok, name)
                self.assertTrue(check.errors)

    def test_reference_cannot_escape_the_workspace(self):
        with tempfile.TemporaryDirectory(prefix="skills-ref-outside-") as outside:
            external = Path(outside) / "private.md"
            external.write_text("private", encoding="utf-8")
            content = app.sample_article().replace("../inputs/source-notes.md", str(external))
            self.workspace.write_file("drafts/article.md", content)
            check = app.check_artifact(self.workspace, "drafts/article.md", "缓存")
            self.assertIn("missing-or-outside-reference", check.errors)

    def test_structural_pass_does_not_certify_a_false_claim(self):
        content = app.sample_article().replace("以下是假设数据，不含性能实测。", "这是故意写错的事实：2 + 3 等于 9。")
        self.workspace.write_file("drafts/article.md", content)
        check = app.check_artifact(self.workspace, "drafts/article.md", "缓存")
        self.assertTrue(check.ok)
        self.assertEqual(check.semantic_correctness, "not-assessed")


class AgentCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="skills-agent-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        app.initialize_samples(self.root)
        self.workspace = app.Workspace(self.root)
        self.loader = app.SkillLoader(self.workspace)

    async def run_fixture(self, scenario="success", model=None, **kwargs):
        model = model or app.fixture_model(self.workspace, scenario, "drafts/article.md", "缓存")
        return await app.execute(model, self.workspace, self.loader, task="写博客：缓存", **kwargs)

    async def test_success_uses_real_tools_and_rereads_the_saved_artifact(self):
        model = app.fixture_model(self.workspace, "success", "drafts/article.md", "缓存")
        with patch.object(self.workspace, "read", wraps=self.workspace.read) as reader:
            result = await self.run_fixture(model=model)
        reader.assert_any_call("drafts/article.md")
        article_reads = [c for c in reader.call_args_list if c.args == ("drafts/article.md",)]
        self.assertEqual(len(article_reads), 2)  # Write receipt, then independent final verification.
        artifact = (self.root / "drafts/article.md").read_text(encoding="utf-8")
        self.assertEqual(result["artifact_check"]["sha256"], app.digest(artifact))
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["artifact_check"]["artifact_read"])
        self.assertEqual(result["artifact_check"]["semantic_correctness"], "not-assessed")
        system = model.requests[0]["messages"][0]["content"]
        self.assertIn("draft 必须为 true", system)
        self.assertEqual({t["function"]["name"] for t in model.requests[0]["tools"]},
                         {"read_file", "write_file", "match_skills", "create_skill"})

    async def test_negative_skip_fixture_fails_even_though_message_claims_saved(self):
        result = await self.run_fixture("skip")
        self.assertEqual(result["runtime_status"], "complete")
        self.assertEqual(result["status"], "validation-failed")
        self.assertFalse(result["artifact_check"]["artifact_read"])
        self.assertFalse((self.root / "drafts/article.md").exists())

    async def test_skip_cannot_pass_using_a_stale_valid_file(self):
        self.workspace.write_file("drafts/article.md", app.sample_article())
        result = await self.run_fixture("skip")
        self.assertTrue(result["artifact_check"]["artifact_read"])
        self.assertIn("artifact-not-written-this-run", result["artifact_check"]["errors"])
        self.assertEqual(result["status"], "validation-failed")

    async def test_written_invalid_artifact_fails_instead_of_grading_final_message(self):
        result = await self.run_fixture("invalid")
        self.assertTrue(result["artifact_check"]["artifact_read"])
        self.assertIn("invalid-frontmatter", result["artifact_check"]["errors"])
        self.assertEqual(result["status"], "validation-failed")

    async def test_changed_disk_content_is_read_and_rejected(self):
        root = self.root
        class ChangeAfterWrite(ScriptedModel):
            async def complete(self, messages, tools):
                if self.position == 2:
                    (root / "drafts/article.md").write_text("not a valid article", encoding="utf-8")
                return await super().complete(messages, tools)
        fixture = app.fixture_model(self.workspace, "success", "drafts/article.md", "缓存")
        result = await self.run_fixture(model=ChangeAfterWrite(fixture.responses))
        self.assertIn("artifact-changed-since-write", result["artifact_check"]["errors"])
        self.assertIn("invalid-frontmatter", result["artifact_check"]["errors"])

    async def test_registered_create_skill_denies_persistence_without_human_approval(self):
        result = await self.run_fixture("learn")
        self.assertEqual(result["tool_errors"], 1)
        self.assertEqual(result["status"], "incomplete")
        self.assertNotIn("explain-cache", self.loader.skills)
        self.assertFalse((self.root / "skills/explain-cache/SKILL.md").exists())

    async def test_registered_approved_create_rescans_and_new_match_returns_text(self):
        self.workspace.approve_proposal("inputs/skill-proposal.json")
        model = app.fixture_model(self.workspace, "learn", "drafts/article.md", "缓存")
        result = await self.run_fixture(model=model)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["scans"], 2)
        tool_messages = [m for req in model.requests for m in req["messages"]
                         if m.get("role") == "tool" and m.get("tool_call_id") == "call-2"]
        self.assertTrue(tool_messages)
        matched = json.loads(tool_messages[0]["content"])["result"]
        self.assertEqual(matched["names"], ["explain-cache"])
        self.assertIn("不编造性能数字", matched["context"])

    async def test_model_cannot_self_approve_using_an_extra_tool_argument(self):
        proposal = json.loads(self.workspace.read("inputs/skill-proposal.json"))
        model = ScriptedModel([app.call("create_skill", dict(proposal, approved=True), 1),
                               {"role": "assistant", "content": "已保存"}])
        result = await self.run_fixture(model=model)
        self.assertEqual(result["tool_errors"], 1)
        self.assertFalse((self.root / "skills/explain-cache/SKILL.md").exists())

    async def test_runtime_reports_boundary_rejection_without_outside_write(self):
        model = ScriptedModel([app.call("write_file", {"path": "../outside.md", "content": "x"}, 1),
                               {"role": "assistant", "content": "已保存"}])
        result = await self.run_fixture(model=model)
        self.assertEqual(result["tool_errors"], 1)
        self.assertFalse(result["artifact_check"]["ok"])

    async def test_runtime_timeout_is_not_a_successful_artifact(self):
        class WaitingModel:
            async def complete(self, messages, tools):
                await asyncio.Event().wait()
        result = await self.run_fixture(model=WaitingModel(), timeout=0.02)
        self.assertEqual(result["runtime_status"], "timeout")
        self.assertEqual(result["status"], "validation-failed")

    async def test_cancellation_closes_live_adapter_and_leaves_no_artifact(self):
        entered = asyncio.Event()
        class WaitingModel:
            closed = False
            async def complete(self, messages, tools):
                entered.set()
                await asyncio.Event().wait()
            async def aclose(self):
                self.closed = True
        model = WaitingModel()
        args = argparse.Namespace(approve_overwrite=[], approve_skill_proposal=[], live=True,
                                  no_skills=False, skill=None, task="写博客", output="drafts/article.md", topic="缓存")
        with patch("app.model_from_env", return_value=model):
            pending = asyncio.create_task(app.run_cli(args, self.root))
            await entered.wait()
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
        self.assertTrue(model.closed)
        self.assertFalse((self.root / "drafts/article.md").exists())

    async def test_live_adapter_is_closed_without_making_a_network_call(self):
        fixture = app.fixture_model(self.workspace, "success", "drafts/article.md", "缓存")
        fixture.closed = False
        async def close():
            fixture.closed = True
        fixture.aclose = close
        args = argparse.Namespace(approve_overwrite=[], approve_skill_proposal=[], live=True,
                                  no_skills=False, skill=None, task="写博客", output="drafts/article.md", topic="缓存")
        with patch("app.model_from_env", return_value=fixture):
            result = await app.run_cli(args, self.root)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(fixture.closed)


if __name__ == "__main__":
    unittest.main()
