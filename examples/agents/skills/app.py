"""A runnable, local Skill loader and artifact-reading writing agent (Python 3.11+)."""
from __future__ import annotations

import argparse
import ast
import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
import tomllib
from urllib.parse import urlsplit

import yaml
from agent_runtime import (ScriptedModel, Tool, atomic_write_text, confined_path,
                           model_from_env, run_agent)

MAX_BYTES = 64 * 1024
NAME = re.compile(r"[a-z][a-z0-9-]{0,47}")
REQUIRED_HEADINGS = ("先给结论", "示例", "参考资料")


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently replacing a rule."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("Skill metadata keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError("File does not exist")
    if not path.is_file():
        raise ValueError("Expected a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("File exceeds the 64 KiB limit")
    return data.decode("utf-8")


def proposal_digest(proposal: dict) -> str:
    return digest(json.dumps(proposal, ensure_ascii=False, sort_keys=True))


def validate_proposal(proposal: dict) -> None:
    if set(proposal) != {"name", "description", "triggers", "content"}:
        raise ValueError("A proposal requires name, description, triggers and content")
    if not isinstance(proposal["name"], str) or not NAME.fullmatch(proposal["name"]):
        raise ValueError("Invalid Skill name")
    for field in ("description", "content"):
        if not isinstance(proposal[field], str) or not proposal[field].strip():
            raise ValueError("Skill description and content must not be empty")
    triggers = proposal["triggers"]
    if (not isinstance(triggers, list) or not 1 <= len(triggers) <= 12
            or any(not isinstance(t, str) or not t.strip() or len(t) > 80 for t in triggers)):
        raise ValueError("Provide 1–12 non-empty trigger strings")
    if not re.search(r"^# .+", proposal["content"], re.M):
        raise ValueError("Skill content requires a top-level heading")
    if len(json.dumps(proposal, ensure_ascii=False).encode("utf-8")) > MAX_BYTES // 2:
        raise ValueError("Skill proposal is too large")


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    triggers: tuple[str, ...]
    content: str
    path: str
    references: tuple[str, ...]


def parse_skill(text: str, relative: str) -> Skill:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Skill requires YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("Unclosed Skill front matter") from error
    metadata = yaml.load("\n".join(lines[1:end]), Loader=UniqueLoader)
    if not isinstance(metadata, dict):
        raise ValueError("Skill metadata must be a mapping")
    if set(metadata) != {"name", "description", "triggers", "references"}:
        raise ValueError("Skill metadata requires name, description, triggers, references")
    content = "\n".join(lines[end + 1:]).strip()
    proposal = {key: metadata[key] for key in ("name", "description", "triggers")}
    proposal["content"] = content
    validate_proposal(proposal)
    references = metadata["references"]
    if (not isinstance(references, list) or len(references) > 4
            or any(not isinstance(p, str) or not p.strip() for p in references)):
        raise ValueError("references must contain at most four relative paths")
    return Skill(proposal["name"], proposal["description"], tuple(proposal["triggers"]),
                 content, relative, tuple(references))


class Workspace:
    """Local-user file boundary. This is not a hostile-process sandbox."""

    def __init__(self, root: Path):
        confined_path(root, ".", allow_root=True)
        self.root = root.resolve()
        self.overwrites: dict[str, str] = {}
        self.approved_proposals: set[str] = set()
        self.written: dict[str, str] = {}
        self.reads: list[str] = []

    def read(self, relative: str) -> str:
        text = read_text(confined_path(self.root, relative))
        self.reads.append(relative)
        return text

    def approve_overwrite(self, relative: str) -> None:
        target = confined_path(self.root, relative)
        if target.relative_to(self.root).parts[0] != "drafts" or target.suffix != ".md":
            raise PermissionError("Only draft Markdown paths can be approved for overwrite")
        self.overwrites[relative] = digest(self.read(relative))

    def approve_proposal(self, relative: str) -> None:
        proposal = json.loads(self.read(relative))
        validate_proposal(proposal)
        self.approved_proposals.add(proposal_digest(proposal))

    def write_file(self, path: str, content: str) -> dict:
        target = confined_path(self.root, path)
        if target.relative_to(self.root).parts[0] != "drafts" or target.suffix != ".md":
            raise PermissionError("write_file can write only Markdown under drafts/")
        if len(content.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Draft exceeds the 64 KiB limit")
        if target.exists():
            current = digest(self.read(path))
            if self.overwrites.get(path) != current:
                raise PermissionError("Overwrite requires external approval for the current file")
            del self.overwrites[path]
        target.parent.mkdir(parents=True, exist_ok=True)
        target = confined_path(self.root, path)
        atomic_write_text(target, content)
        # Record actual bytes decoded from disk, including the platform's line endings.
        written_text = self.read(path)
        self.written[path] = digest(written_text)
        return {"path": path, "bytes": len(written_text.encode("utf-8")), "sha256": digest(written_text)}


class SkillLoader:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.skills: dict[str, Skill] = {}
        self.scans = 0
        self.scan()

    def scan(self) -> None:
        directory = confined_path(self.workspace.root, "skills")
        if not directory.is_dir():
            raise ValueError("Initialize a skills/ directory first")
        fresh = {}
        for path in sorted(directory.glob("*/SKILL.md")):
            relative = path.relative_to(self.workspace.root).as_posix()
            skill = parse_skill(self.workspace.read(relative), relative)
            if skill.name != path.parent.name or skill.name in fresh:
                raise ValueError("Skill names must be unique and match directory names")
            fresh[skill.name] = skill
        self.skills = fresh
        self.scans += 1

    def select(self, task: str, names: list[str] | None = None) -> list[Skill]:
        if names is not None:
            missing = set(names) - self.skills.keys()
            if missing:
                raise ValueError("Unknown Skill: " + ", ".join(sorted(missing)))
            return [self.skills[name] for name in dict.fromkeys(names)]
        folded = task.casefold()
        return [skill for skill in self.skills.values()
                if any(trigger.casefold() in folded for trigger in skill.triggers)]

    def context(self, selected: list[Skill]) -> str:
        parts = []
        for skill in selected:
            parts.append(f"## Skill {skill.name}\n{skill.description}\n{skill.content}")
            skill_root = confined_path(self.workspace.root, str(Path(skill.path).parent))
            for reference in skill.references:
                target = confined_path(skill_root, reference)
                relative = target.relative_to(self.workspace.root).as_posix()
                parts.append(f"### Reference {reference}\n{self.workspace.read(relative)}")
        result = "\n\n".join(parts)
        if len(result.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Selected Skill context exceeds 64 KiB")
        return result

    def create_skill(self, name: str, description: str, triggers: list[str], content: str) -> dict:
        proposal = dict(name=name, description=description, triggers=triggers, content=content)
        validate_proposal(proposal)
        approved = proposal_digest(proposal)
        if approved not in self.workspace.approved_proposals:
            raise PermissionError("Persisting a Skill requires explicit approval of this exact proposal")
        relative = f"skills/{name}/SKILL.md"
        target = confined_path(self.workspace.root, relative)
        if target.exists() or target.parent.exists():
            raise FileExistsError("create_skill never overwrites an existing Skill directory")
        metadata = dict(name=name, description=description, triggers=triggers, references=[])
        text = "---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + "---\n\n" + content
        parse_skill(text, relative)
        target.parent.mkdir()
        atomic_write_text(confined_path(self.workspace.root, relative), text)
        self.workspace.approved_proposals.remove(approved)
        self.scan()  # Replace the registry immediately; the next match_skills call sees it.
        return {"created": relative, "available": sorted(self.skills), "scan": self.scans}


def schema(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def tools_for(workspace: Workspace, loader: SkillLoader) -> list[Tool]:
    string = {"type": "string", "minLength": 1}
    def match_skills(task: str) -> dict:
        selected = loader.select(task)
        return {"names": [s.name for s in selected], "context": loader.context(selected)}
    return [
        Tool("read_file", "Read a UTF-8 file inside the workspace (64 KiB maximum).",
             schema({"path": string}), lambda path: {"content": workspace.read(path)}),
        Tool("write_file", "Write a draft Markdown file; host approval is required to overwrite.",
             schema({"path": string, "content": string}), workspace.write_file),
        Tool("match_skills", "Match the current registry and return selected Skill text and references.",
             schema({"task": string}), match_skills),
        Tool("create_skill", "Persist exactly a human-approved proposal; unapproved calls are rejected.",
             schema({"name": string, "description": string,
                     "triggers": {"type": "array", "items": string, "minItems": 1, "maxItems": 12},
                     "content": string}), loader.create_skill),
    ]


@dataclass
class ArtifactCheck:
    ok: bool
    path: str
    artifact_read: bool
    sha256: str | None
    errors: list[str]
    semantic_correctness: str = "not-assessed"


def check_artifact(workspace: Workspace, path: str, required_text: str) -> ArtifactCheck:
    """Always reread disk; never accept the assistant's final save message as evidence."""
    errors = []
    try:
        text = workspace.read(path)
    except FileNotFoundError:
        return ArtifactCheck(False, path, False, None, ["missing-artifact"])
    except (OSError, ValueError, UnicodeError) as error:
        return ArtifactCheck(False, path, False, None, ["artifact-unreadable: " + type(error).__name__])
    if path not in workspace.written:
        errors.append("artifact-not-written-this-run")
    elif digest(text) != workspace.written[path]:
        errors.append("artifact-changed-since-write")
    lines = text.splitlines()
    body = ""
    try:
        if not lines or lines[0] != "+++":
            raise ValueError("Expected TOML front matter")
        end = lines.index("+++", 1)
        metadata = tomllib.loads("\n".join(lines[1:end]))
        body = "\n".join(lines[end + 1:])
        if any(not isinstance(metadata.get(k), str) or not metadata[k].strip()
               for k in ("title", "description")):
            errors.append("frontmatter-title-or-description")
        if metadata.get("draft") is not True:
            errors.append("frontmatter-draft-must-be-true")
        tags = metadata.get("tags")
        if (not isinstance(tags, list) or not tags
                or any(not isinstance(t, str) or not t.strip() for t in tags)):
            errors.append("frontmatter-tags")
    except (ValueError, tomllib.TOMLDecodeError):
        errors.append("invalid-frontmatter")
    prose, blocks, opened, current = [], [], None, []
    language = ""
    for line in body.splitlines():
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if opened is None and fence:
            opened = fence.group(1)
            language = fence.group(2).strip()
            current = []
        elif opened is not None:
            if (fence and fence.group(1)[0] == opened[0]
                    and len(fence.group(1)) >= len(opened) and not fence.group(2).strip()):
                blocks.append((language, "\n".join(current)))
                opened = None
            else:
                current.append(line)
        else:
            prose.append(line)
    if opened is not None:
        errors.append("unclosed-code-fence")
    prose_text = "\n".join(prose)
    sections = re.split(r"^## (.+)\s*$", prose_text, flags=re.M)
    section_map = dict(zip(sections[1::2], sections[2::2]))
    for heading in REQUIRED_HEADINGS:
        if not section_map.get(heading, "").strip():
            errors.append("missing-section: " + heading)
    if required_text.casefold() not in prose_text.casefold():
        errors.append("missing-expected-content: " + required_text)
    python_blocks = [code for lang, code in blocks if lang == "python" and code.strip()]
    if not python_blocks:
        errors.append("missing-python-code")
    for code in python_blocks:
        try:
            if not ast.parse(code).body:
                errors.append("empty-python-program")
        except SyntaxError:
            errors.append("invalid-python-syntax")
    links = re.findall(r"\[([^\]\n]+)\]\(([^\s)]+)\)", section_map.get("参考资料", ""))
    if not links:
        errors.append("missing-reference")
    for _, target in links:
        try:
            url = urlsplit(target)
        except ValueError:
            errors.append("invalid-reference-target")
            continue
        if url.scheme:
            if url.scheme != "https" or not url.netloc:
                errors.append("invalid-reference-target")
        else:
            # References may use ../inputs from drafts/, but their normalized target must stay in root.
            try:
                candidate = (workspace.root / path).parent / url.path
                relative = candidate.resolve().relative_to(workspace.root).as_posix()
                # Check every lexical component too, so resolution cannot hide a symlink.
                for parent in [candidate, *candidate.parents]:
                    if parent == workspace.root:
                        break
                    if parent.is_symlink():
                        raise ValueError("Symlink reference")
                read_text(confined_path(workspace.root, relative))
            except (OSError, ValueError, UnicodeError):
                errors.append("missing-or-outside-reference")
    return ArtifactCheck(not errors, path, True, digest(text), errors)


async def execute(model, workspace: Workspace, loader: SkillLoader, *, task: str,
                  artifact: str = "drafts/article.md", topic: str = "缓存",
                  names: list[str] | None = None, timeout: float = 30.0) -> dict:
    workspace.written.clear()  # A previous run's valid file is not a new artifact.
    selected = loader.select(task, names)
    context = loader.context(selected)
    system = ("你是教学写作助手。用户任务和工具权限优先于下面可信的示例 Skill。"
              "先读 inputs/source-notes.md，再把完整草稿写到指定路径。"
              "不要把长期偏好当作已经获准保存，create_skill 的授权由程序检查。"
              "完成声明不能代替文件；稍后程序会从磁盘读取并检查。\n" + context)
    result = await run_agent(model, system, f"{task}\n产物路径：{artifact}\n正文主题：{topic}",
                             tools_for(workspace, loader), max_turns=8,
                             max_tool_calls=16, timeout=timeout)
    artifact_check = check_artifact(workspace, artifact, topic)
    tool_errors = [json.loads(m["content"]) for m in result.messages
                   if m.get("role") == "tool" and json.loads(m["content"]).get("ok") is False]
    status = ("complete" if result.status == "complete" and artifact_check.ok and not tool_errors
              else "validation-failed" if not artifact_check.ok else "incomplete")
    return {"status": status, "runtime_status": result.status,
            "selected_skills": [s.name for s in selected], "scans": loader.scans,
            "available_skills": sorted(loader.skills), "tool_errors": len(tool_errors),
            "artifact_check": asdict(artifact_check)}


def sample_article(topic: str = "缓存") -> str:
    return ('+++\ntitle = "字典缓存示例"\ndescription = "一个合成的缓存草稿"\n'
            'draft = true\ntags = ["Python"]\n+++\n\n## 先给结论\n'
            + topic + '先按键查已有值，缺失时再计算。以下是假设数据，不含性能实测。\n\n'
            '## 示例\n假设输入固定，同一进程中重复请求相同的键：\n\n'
            '```python\ncache = {}\nkey = "demo"\nif key not in cache:\n'
            '    cache[key] = 2 + 3\nprint(cache[key])\n```\n\n'
            '原始数据变化但不更新缓存时，旧结果仍可能被读取。\n\n## 参考资料\n'
            '[合成任务资料](../inputs/source-notes.md)\n')


def call(name: str, arguments: dict, number: int) -> dict:
    return {"role": "assistant", "content": None, "tool_calls": [{"id": f"call-{number}",
            "type": "function", "function": {"name": name,
            "arguments": json.dumps(arguments, ensure_ascii=False)}}]}


def fixture_model(workspace: Workspace, scenario: str, artifact: str, topic: str) -> ScriptedModel:
    if scenario == "skip":
        return ScriptedModel([{"role": "assistant", "content": "文章已保存。"}])
    responses = []
    if scenario == "learn":
        proposal = json.loads(workspace.read("inputs/skill-proposal.json"))
        responses.extend([call("create_skill", proposal, 1),
                          call("match_skills", {"task": "缓存检查"}, 2)])
    responses.append(call("read_file", {"path": "inputs/source-notes.md"}, 3))
    content = "缺少 front matter 和代码的文章" if scenario == "invalid" else sample_article(topic)
    responses.append(call("write_file", {"path": artifact, "content": content}, 4))
    responses.append({"role": "assistant", "content": "文章已保存。"})
    return ScriptedModel(responses)


def initialize_samples(root: Path) -> None:
    """Seed explicit built-in demo files, never overwrite existing user files."""
    source = Path(__file__).resolve().parent
    confined_path(root, ".", allow_root=True)
    for directory in ("drafts", "inputs", "skills"):
        confined_path(root, directory).mkdir(exist_ok=True)
    for package_dir, target_dir in (("sample-skills", "skills"), ("sample-data", "inputs")):
        for item in sorted((source / package_dir).rglob("*")):
            if not item.is_file():
                continue
            relative = (Path(target_dir) / item.relative_to(source / package_dir)).as_posix()
            target = confined_path(root, relative)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(confined_path(root, relative), read_text(item))


async def run_cli(args, root: Path) -> dict:
    initialize_samples(root)
    workspace = Workspace(root)
    for relative in args.approve_overwrite:
        workspace.approve_overwrite(relative)
    for relative in args.approve_skill_proposal:
        workspace.approve_proposal(relative)
    loader = SkillLoader(workspace)
    names = [] if args.no_skills else args.skill
    model = model_from_env() if args.live else fixture_model(workspace, args.fixture, args.output, args.topic)
    try:
        return await execute(model, workspace, loader, task=args.task, artifact=args.output,
                             topic=args.topic, names=names)
    finally:
        if args.live:
            await model.aclose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="Explicit data directory; otherwise a temporary directory is cleaned up")
    parser.add_argument("--live", action="store_true", help="Use configured live API instead of fixtures")
    parser.add_argument("--fixture", choices=("success", "skip", "invalid", "learn"), default="success")
    parser.add_argument("--task", default="写一篇解释缓存的博客草稿，依据提供的合成资料。")
    parser.add_argument("--topic", default="缓存", help="Text that must appear in the article prose")
    parser.add_argument("--output", default="drafts/article.md")
    choose = parser.add_mutually_exclusive_group()
    choose.add_argument("--skill", action="append", help="Exact Skill name; repeat to combine")
    choose.add_argument("--no-skills", action="store_true")
    parser.add_argument("--approve-overwrite", action="append", default=[], metavar="PATH")
    parser.add_argument("--approve-skill-proposal", action="append", default=[], metavar="PATH")
    args = parser.parse_args(argv)
    print("mode=live" if args.live else f"mode=fixture scenario={args.fixture} (本地固定响应)")
    try:
        if args.workspace:
            args.workspace.mkdir(parents=True, exist_ok=True)
            result = asyncio.run(run_cli(args, args.workspace))
        else:
            with tempfile.TemporaryDirectory(prefix="skill-agent-") as temporary:
                result = asyncio.run(run_cli(args, Path(temporary)))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "complete" else 1
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
