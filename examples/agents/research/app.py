"""Run the offline corpus demonstration, or an explicitly configured live model."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
import tempfile
import uuid

# This example creates research data only in a temporary/explicit workspace.
sys.dont_write_bytecode = True

from agent_runtime import atomic_write_text, confined_path, model_from_env

if __package__:
    from .fixture_model import CorpusFixtureModel
    from .pipeline import Limits, render_report, run_research
    from .sources import CorpusProvider
else:
    from fixture_model import CorpusFixtureModel
    from pipeline import Limits, render_report, run_research
    from sources import CorpusProvider

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus.json"
DEFAULT_TASK = "整理南岚团队两份合成规程中的研究记录与发布复核要求。"


def positive_seconds(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("time must be finite and positive")
    return number


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--task", default=DEFAULT_TASK)
    result.add_argument("--corpus", type=Path, help="explicit local corpus manifest (UTF-8 JSON)")
    result.add_argument("--live", action="store_true", help="use a live model; source tools remain local-only")
    result.add_argument("--workspace", type=Path, help="persist a new run subdirectory here")
    result.add_argument("--timeout", type=positive_seconds, default=60.0)
    result.add_argument("--request-timeout", type=positive_seconds, default=10.0)
    result.add_argument("--max-revisions", type=int, choices=range(6), default=2)
    return result


def save_run(result, workspace: Path):
    workspace.mkdir(parents=True, exist_ok=True)
    run_dir = confined_path(workspace, "run-" + uuid.uuid4().hex)
    run_dir.mkdir()
    for name, value in (("result", asdict(result)), ("plan", result.plan), ("sources", result.sources),
                        ("notes", result.notes), ("drafts", result.drafts), ("checks", result.checks)):
        atomic_write_text(confined_path(run_dir, name + ".json"),
                          json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    atomic_write_text(confined_path(run_dir, "report.md"), render_report(result))
    return run_dir


async def async_main(args) -> int:
    model = None
    try:
        if args.live and args.corpus is None:
            raise ValueError("--live requires --corpus; only explicitly supplied local files are researched")
        provider = CorpusProvider(args.corpus or FIXTURE_CORPUS, request_timeout=args.request_timeout)
        limits = Limits(total_timeout=args.timeout, request_timeout=args.request_timeout,
                        max_revisions=args.max_revisions)
        model = model_from_env() if args.live else CorpusFixtureModel()
        mode = "live" if args.live else "fixture"
        print(f"mode={mode} (" + ("联网模型；资料工具只读本地文件" if args.live
                                   else "本地固定响应；无联网检索") + ")")
        print("corpus=" + provider.label)
        result = await run_research(args.task, model, provider, limits=limits, mode=mode)
        print(f'plan.questions={len(result.plan.get("questions", []))}')
        searches = sum(e["event"] == "search" for e in result.events)
        fetches = sum(e["event"] == "fetch" for e in result.events)
        print(f"tool.search={searches} tool.fetch={fetches} notes={len(result.notes)}")
        for check in result.checks:
            issues = ",".join(check["mechanical_issues"]) or "none"
            print(f'check revision={check["revision"]} passed={str(check["passed"]).lower()} issues={issues}')
        print("status=" + result.status)
        if result.report:
            used = {n for c in result.report["claims"] for n in c["note_ids"]}
            print("citations=" + ",".join(n["id"] + ":" + n["source_id"]
                                         for n in result.notes if n["id"] in used))
        for error in result.errors:
            print("error=" + error)
        if args.workspace is not None:
            location = save_run(result, args.workspace)
            print("workspace=" + str(location))
        else:
            with tempfile.TemporaryDirectory(prefix="research-agent-") as temporary:
                save_run(result, Path(temporary))
            print("workspace=temporary (已清理；用 --workspace 显式保留)")
        return 0 if result.status == "complete" else (124 if result.status == "timeout" else 1)
    except ValueError as error:
        print("configuration_error=" + str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print("run_error=" + type(error).__name__, file=sys.stderr)
        return 1
    finally:
        if args.live and model is not None:
            await model.aclose()


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("cancelled; work is incomplete", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
