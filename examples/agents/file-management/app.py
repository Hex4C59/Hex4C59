"""File operations with explicit approval, durable backups and restart recovery."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from typing import Callable
import uuid

from agent_runtime import Tool, ScriptedModel, model_from_env, run_agent, confined_path


STATE_DIR = ".file-agent"
MAX_BYTES = 1024 * 1024
MAX_PENDING = 20


class FileAgentError(ValueError):
    pass


class RecoveryRequired(FileAgentError):
    pass


class FileManager:
    """A local-user boundary. Other programs must not race directory changes."""

    def __init__(self, workspace: Path, *, fault: Callable | None = None):
        given = Path(workspace).absolute()
        if given.is_symlink() or not given.is_dir():
            raise FileAgentError("工作区必须是现有目录，不能是符号链接")
        self.root = given.resolve()
        home = Path.home().resolve()
        if self.root == home or self.root in home.parents:
            raise FileAgentError("不能把 HOME 或它的祖先作为工作区")
        if any((p / ".git").exists() for p in (self.root, *self.root.parents)):
            raise FileAgentError("请使用独立练习目录，不能使用 Git checkout")
        self.control = self.root / STATE_DIR
        if self.control.is_symlink():
            raise FileAgentError("状态目录不能是符号链接")
        self.control.mkdir(mode=0o700, exist_ok=True)
        self.staging = self.control / "staging"
        if self.staging.is_symlink():
            raise FileAgentError("暂存目录不能是符号链接")
        self.staging.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.control, 0o700)
        os.chmod(self.staging, 0o700)
        self.fault = fault or (lambda point, row: None)
        with self._locked() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RecoveryRequired("日志版本不支持，未修改业务文件")
            if version == 0:
                if conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise RecoveryRequired("无法识别已有日志，未重建数据库")
                with conn:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("""CREATE TABLE operations (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        id TEXT UNIQUE NOT NULL,
                        action TEXT NOT NULL,
                        source TEXT NOT NULL,
                        destination TEXT,
                        digest TEXT NOT NULL,
                        image BLOB NOT NULL,
                        source_stamp TEXT NOT NULL,
                        target_stamp TEXT,
                        execution_order INTEGER,
                        state TEXT NOT NULL,
                        error TEXT NOT NULL DEFAULT ''
                    )""")
                    conn.execute("PRAGMA user_version=1")
            self._recover(conn)

    def _control_files(self):
        for name in ("lock.sqlite3", "lock.sqlite3-journal", "journal.sqlite3",
                     "journal.sqlite3-journal", "journal.sqlite3-wal", "journal.sqlite3-shm"):
            p = self.control / name
            if p.is_symlink() or (p.exists() and (not p.is_file() or p.stat().st_nlink != 1)):
                raise RecoveryRequired("状态文件必须是独立普通文件")
        if self.control.is_symlink() or self.staging.is_symlink():
            raise RecoveryRequired("状态路径发生变化")

    @contextmanager
    def _locked(self):
        self._control_files()
        # This second SQLite database holds an application-wide file lock across
        # commits to the journal. Process exit releases it; no stale PID lock.
        with closing(sqlite3.connect(self.control / "lock.sqlite3", timeout=0.2)) as lock:
            try:
                lock.execute("BEGIN EXCLUSIVE")
            except sqlite3.OperationalError as exc:
                raise FileAgentError("工作区正被另一个应用调用占用") from exc
            self._control_files()
            with closing(sqlite3.connect(self.control / "journal.sqlite3")) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA synchronous=FULL")
                for name in ("lock.sqlite3", "journal.sqlite3"):
                    os.chmod(self.control / name, 0o600)
                yield conn

    @contextmanager
    def _ready(self):
        with self._locked() as conn:
            self._recover(conn)
            yield conn

    def _path(self, relative: str, *, allow_root: bool = False) -> Path:
        if not isinstance(relative, str) or STATE_DIR in Path(relative).parts:
            raise FileAgentError("不能操作应用状态目录")
        try:
            p = confined_path(self.root, relative, allow_root=allow_root)
        except (ValueError, OSError) as exc:
            raise FileAgentError(str(exc)) from exc
        if not p.parent.is_dir() and p != self.root:
            raise FileAgentError("目标父目录必须已存在")
        cursor = self.root
        for part in p.relative_to(self.root).parts:
            if cursor.is_dir():
                child = cursor / part
                if child.exists() and part not in os.listdir(cursor):
                    raise FileAgentError("路径必须使用目录列出的实际大小写")
            cursor = cursor / part
        cursor = p if p.exists() else p.parent
        if cursor.stat().st_dev != self.root.stat().st_dev:
            raise FileAgentError("不支持跨文件系统操作")
        return p

    @staticmethod
    def _stamp(p: Path, *, managed: bool = False) -> dict:
        info = p.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink not in ((1, 2) if managed else (1,)):
            raise FileAgentError("只支持普通文件；目录、符号链接和外部硬链接不支持")
        if info.st_mode & (stat.S_ISUID | stat.S_ISGID):
            raise FileAgentError("不支持 setuid/setgid 特殊权限文件")
        if info.st_size > MAX_BYTES:
            raise FileAgentError("文件超过 1 MiB 教学上限")
        data = p.read_bytes()
        after = p.lstat()
        if (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise FileAgentError("读取期间文件发生变化")
        return {"dev": info.st_dev, "ino": info.st_ino, "size": len(data),
                "mtime": info.st_mtime_ns, "mode": stat.S_IMODE(info.st_mode),
                "sha256": hashlib.sha256(data).hexdigest()}

    @staticmethod
    def _sync_dir(p: Path):
        # Directory fsync is available on the POSIX hosts used for this example.
        # This demo does not claim power-loss guarantees on other filesystems.
        if os.name == "posix":
            fd = os.open(p, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def _row(self, conn, operation_id: str) -> dict:
        row = conn.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
        if row is None:
            raise FileAgentError("没有该操作")
        result = dict(row)
        self._validate_row(result)
        return result

    @staticmethod
    def _validate_row(row: dict):
        states = {"pending", "cancelled", "applying", "applied", "undoing", "undone", "failed"}
        if row["action"] not in {"move", "copy", "delete"} or row["state"] not in states:
            raise RecoveryRequired("日志操作或状态无效")
        if len(row["image"]) > MAX_BYTES or hashlib.sha256(row["image"]).hexdigest() != row["digest"]:
            raise RecoveryRequired("日志备份校验失败，未改业务文件")
        try:
            source = json.loads(row["source_stamp"])
            if source["sha256"] != row["digest"] or source["size"] != len(row["image"]):
                raise ValueError("snapshot mismatch")
            if row["target_stamp"] is not None and json.loads(row["target_stamp"])["sha256"] != row["digest"]:
                raise ValueError("target mismatch")
        except (ValueError, KeyError, TypeError) as exc:
            raise RecoveryRequired("日志文件摘要无效") from exc

    @staticmethod
    def _public(row: dict) -> dict:
        return {k: row[k] for k in ("id", "action", "source", "destination", "state", "error")} | {
            "bytes": len(row["image"]), "sha256": row["digest"]}

    def _persist(self, conn, row: dict, state: str, *, error: str = "", refresh: bool = False):
        try:
            order = row["execution_order"]
            if state == "applying" and order is None:
                order = conn.execute("SELECT coalesce(max(execution_order), 0) + 1 FROM operations").fetchone()[0]
            conn.execute("UPDATE operations SET state=?, target_stamp=?, execution_order=?, error=? WHERE id=?",
                         (state, row["target_stamp"], order, error, row["id"]))
            # Undoing B->C recreates B with a new inode. The preceding A->B
            # journal entry must recognize that app-owned restored file.
            restore = self._stage_path(row, "restore")
            source = self._path(row["source"])
            if refresh and restore.exists() and source.exists() and source.samefile(restore):
                predecessor = conn.execute("""SELECT id FROM operations WHERE execution_order<? AND state='applied'
                    AND destination=? AND digest=? ORDER BY execution_order DESC LIMIT 1""",
                    (order, row["source"], row["digest"])).fetchone()
                if predecessor:
                    conn.execute("UPDATE operations SET target_stamp=? WHERE id=?",
                                 (json.dumps(self._stamp(source, managed=True)), predecessor["id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        row["state"], row["error"], row["execution_order"] = state, error, order

    def _stage_path(self, row: dict, suffix: str) -> Path:
        if len(row["id"]) != 32 or any(c not in "0123456789abcdef" for c in row["id"]):
            raise RecoveryRequired("日志操作编号无效")
        return self.staging / (row["id"] + "." + suffix)

    def _stage(self, row: dict, suffix: str) -> Path:
        p = self._stage_path(row, suffix)
        if p.is_symlink():
            raise RecoveryRequired("暂存文件不能是符号链接")
        if p.exists():
            if self._stamp(p, managed=True)["sha256"] != row["digest"]:
                raise RecoveryRequired("暂存内容与日志备份不符")
            return p
        if hashlib.sha256(row["image"]).hexdigest() != row["digest"]:
            raise RecoveryRequired("日志备份校验失败，拒绝恢复")
        created = False
        try:
            with p.open("xb") as out:
                created = True
                out.write(row["image"])
                out.flush()
                os.fsync(out.fileno())
            os.chmod(p, json.loads(row["source_stamp"])["mode"] & 0o777)
            self._sync_dir(self.staging)
        except Exception:
            if created:
                p.unlink(missing_ok=True)
            raise
        return p

    def _cleanup(self, row: dict):
        for suffix in ("apply", "restore"):
            p = self._stage_path(row, suffix)
            if p.is_symlink():
                raise RecoveryRequired("拒绝清理异常暂存路径")
            if p.exists():
                if not p.is_file():
                    raise RecoveryRequired("暂存路径类型不符")
                p.unlink()
        self._sync_dir(self.staging)

    def _owned_target(self, row: dict) -> Path | None:
        if not row["destination"]:
            return None
        p = self._path(row["destination"])
        stage = self._stage_path(row, "apply")
        managed = stage.exists() and not stage.is_symlink() and p.exists() and p.samefile(stage)
        if p.exists() and self._stamp(p, managed=managed) != json.loads(row["target_stamp"]):
            raise RecoveryRequired("目标文件已变化；保留现状，拒绝删除或覆盖")
        return p

    def _restore_source(self, row: dict):
        p = self._path(row["source"])
        restore = self._stage_path(row, "restore")
        if p.exists():
            owned = restore.exists() and not restore.is_symlink() and p.samefile(restore)
            if not owned and self._stamp(p) != json.loads(row["source_stamp"]):
                raise RecoveryRequired("原路径已被占用或修改；拒绝覆盖")
            if self._stamp(p, managed=owned)["sha256"] != row["digest"]:
                raise RecoveryRequired("恢复中的文件内容不符")
            return
        stage = self._stage(row, "restore")
        os.link(stage, p)  # Atomic no-replace: an occupied name raises.
        self._sync_dir(p.parent)

    def _rollback_apply(self, row: dict):
        target = self._owned_target(row)  # Validate before changing either side.
        if row["action"] in ("move", "delete"):
            self._restore_source(row)
        if target is not None and target.exists():
            target.unlink()
            self._sync_dir(target.parent)

    def _finish_undo(self, row: dict):
        target = self._owned_target(row)
        if row["action"] in ("move", "delete"):
            self._restore_source(row)
        if target is not None and target.exists():
            target.unlink()
            self._sync_dir(target.parent)

    def _recover(self, conn):
        rows = [dict(r) for r in conn.execute("SELECT * FROM operations ORDER BY execution_order DESC, seq DESC")]
        for row in rows:
            try:
                self._validate_row(row)
                if row["state"] == "applying":
                    self._rollback_apply(row)
                    self._persist(conn, row, "failed", error="未完成的执行已回滚", refresh=True)
                elif row["state"] == "undoing":
                    self._finish_undo(row)
                    self._persist(conn, row, "undone", refresh=True)
                self._cleanup(row)
            except Exception as exc:
                raise RecoveryRequired(f"操作 {row['id']} 需要恢复；未宣称完成：{exc}") from exc

    def list_directory(self, directory: str = "") -> dict:
        with self._ready():
            p = self._path(directory, allow_root=True)
            if not p.is_dir():
                raise FileAgentError("不是目录")
            return {"entries": [{"name": q.name,
                                  "type": "symlink-blocked" if q.is_symlink() else
                                  "directory" if q.is_dir() else "file"}
                                 for q in sorted(p.iterdir()) if q.name != STATE_DIR]}

    def preview(self) -> list[dict]:
        with self._ready() as conn:
            return [self._public(dict(r)) for r in conn.execute(
                "SELECT * FROM operations WHERE state='pending' ORDER BY seq")]

    def history(self) -> list[dict]:
        with self._ready() as conn:
            return [self._public(dict(r)) for r in conn.execute("SELECT * FROM operations ORDER BY seq")]

    def queue(self, action: str, source: str, destination: str | None = None) -> dict:
        with self._ready() as conn:
            if action not in {"move", "copy", "delete"}:
                raise FileAgentError("只支持 move/copy/delete")
            if conn.execute("SELECT count(*) FROM operations WHERE state='pending'").fetchone()[0] >= MAX_PENDING:
                raise FileAgentError("待确认队列已达20项上限")
            src = self._path(source)
            source = src.relative_to(self.root).as_posix()
            stamp = self._stamp(src)
            image = src.read_bytes()
            if hashlib.sha256(image).hexdigest() != stamp["sha256"]:
                raise FileAgentError("读取期间文件发生变化")
            if action == "delete":
                if destination is not None:
                    raise FileAgentError("删除不接受目标路径")
            else:
                if not destination:
                    raise FileAgentError("移动/复制需要目标路径")
                dst = self._path(destination)
                if dst.exists() or src == dst:
                    raise FileAgentError("目标已存在，拒绝覆盖")
                destination = dst.relative_to(self.root).as_posix()
            operation_id = uuid.uuid4().hex
            with conn:
                conn.execute("""INSERT INTO operations
                    (id,action,source,destination,digest,image,source_stamp,state)
                    VALUES (?,?,?,?,?,?,?,'pending')""",
                    (operation_id, action, source, destination, stamp["sha256"], image, json.dumps(stamp)))
            return self._public(self._row(conn, operation_id))

    @staticmethod
    def _approval(operation_id: str, approval: str, verb: str):
        if approval != f"{verb} {operation_id}":
            raise FileAgentError("未收到该操作的完整确认口令，未改业务文件")

    def cancel(self, operation_id: str) -> dict:
        with self._ready() as conn:
            row = self._row(conn, operation_id)
            if row["state"] != "pending":
                raise FileAgentError("只能取消待确认操作")
            self._persist(conn, row, "cancelled")
            return self._public(row)

    def apply(self, operation_id: str, approval: str) -> dict:
        with self._ready() as conn:
            row = self._row(conn, operation_id)
            if row["state"] != "pending":
                raise FileAgentError("不是待确认操作，不能重复执行")
            self._approval(operation_id, approval, "APPROVE")
            src = self._path(row["source"])
            if self._stamp(src) != json.loads(row["source_stamp"]):
                raise FileAgentError("源文件自预览后已变化，请取消并重新提案")
            dst = self._path(row["destination"]) if row["destination"] else None
            if dst is not None and dst.exists():
                raise FileAgentError("目标已被占用，拒绝覆盖")
            stage = self._stage(row, "apply") if dst else None
            row["target_stamp"] = json.dumps(self._stamp(stage)) if stage else None
            try:
                self._persist(conn, row, "applying")  # Commit before any business mutation.
            except Exception:
                self._cleanup(row)
                raise
            try:
                self.fault("after_prepare", row)
                if dst is not None:
                    os.link(stage, dst)
                    self._sync_dir(dst.parent)
                self.fault("after_target", row)
                if row["action"] in ("move", "delete"):
                    src.unlink()
                    self._sync_dir(src.parent)
                self.fault("after_source", row)
                self._persist(conn, row, "applied")
            except Exception as exc:
                # If a wrapper failed after commit, the durable outcome wins.
                # Do not undo an applied operation and leave an applied record.
                try:
                    recorded = self._row(conn, operation_id)
                except Exception as unknown:
                    raise RecoveryRequired("无法确认日志提交状态，请重新打开应用恢复") from unknown
                if recorded["state"] == "applied":
                    raise RecoveryRequired("日志已确认执行，请重新打开查看状态或申请撤销") from exc
                try:
                    self._rollback_apply(row)
                    self._persist(conn, row, "failed", error=str(exc), refresh=True)
                    self._cleanup(row)
                except Exception as recovery:
                    raise RecoveryRequired("执行失败，恢复未完成；请排除冲突后重新打开应用") from recovery
                raise FileAgentError("执行失败，业务文件已回滚") from exc
            self._cleanup(row)
            return self._public(row)

    def undo(self, operation_id: str, approval: str) -> dict:
        with self._ready() as conn:
            latest = conn.execute("SELECT id FROM operations WHERE state='applied' ORDER BY execution_order DESC LIMIT 1").fetchone()
            if latest is None or operation_id != latest["id"]:
                raise FileAgentError("只能撤销最近一条已执行操作")
            row = self._row(conn, operation_id)
            self._approval(operation_id, approval, "UNDO")
            target = self._owned_target(row)
            if target is not None and not target.exists():
                raise FileAgentError("目标已不在原处，拒绝猜测撤销")
            if row["action"] in ("move", "delete") and self._path(row["source"]).exists():
                raise FileAgentError("原路径被占用，拒绝覆盖")
            self._persist(conn, row, "undoing")
            try:
                self._finish_undo(row)
                self.fault("after_undo_files", row)
                self._persist(conn, row, "undone", refresh=True)
            except Exception as exc:
                raise RecoveryRequired("撤销尚未确认完成；重新打开后按日志继续恢复") from exc
            self._cleanup(row)
            return self._public(row)


def tools_for(manager: FileManager) -> list[Tool]:
    return [
        Tool("list_directory", "列出工作区目录；符号链接标为禁止使用", {
            "type": "object", "properties": {"directory": {"type": "string"}},
            "additionalProperties": False}, manager.list_directory),
        Tool("queue_operation", "仅提交待确认提案，不执行文件变更", {
            "type": "object", "properties": {
                "action": {"type": "string", "enum": ["move", "copy", "delete"]},
                "source": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["action", "source"], "additionalProperties": False}, manager.queue),
        Tool("preview", "查看尚未执行的操作与内容摘要", {
            "type": "object", "properties": {}, "additionalProperties": False}, manager.preview),
    ]


def fixture_call(name: str, arguments: dict, call_id: str) -> dict:
    return {"id": call_id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(arguments)}}


async def propose_with_model(manager: FileManager, task: str, *, live: bool = False):
    if live:
        model = model_from_env()
    else:
        model = ScriptedModel([
            {"role": "assistant", "content": None, "tool_calls": [
                fixture_call("queue_operation", {"action": "move", "source": "notes.txt", "destination": "sorted/notes.txt"}, "m"),
                fixture_call("queue_operation", {"action": "delete", "source": "trash.txt"}, "d")]},
            {"role": "assistant", "content": "提案已保存，文件尚未变更，请由用户在 CLI 审批。"},
        ])
    try:
        return await run_agent(model,
            "你只生成工作区文件整理提案。先查看目录；变更只能提交队列。不能声称文件已经执行，批准不由你决定。",
            task, tools_for(manager), max_turns=8, max_tool_calls=20, timeout=60)
    finally:
        if live:
            await model.aclose()


async def fixture_demo():
    with tempfile.TemporaryDirectory(prefix="file-agent-fixture-") as directory:
        root = Path(directory)
        (root / "sorted").mkdir()
        (root / "notes.txt").write_text("keep this note\n", encoding="utf-8")
        (root / "trash.txt").write_text("recover this delete\n", encoding="utf-8")
        manager = FileManager(root)
        result = await propose_with_model(manager, "整理合成文件")
        pending = manager.preview()
        print(f"[fixture 本地固定响应] model={result.status}; pending={len(pending)}")
        print(f"[fixture] dry-run: notes={ (root / 'notes.txt').exists() }; trash={ (root / 'trash.txt').exists() }")
        if result.status != "complete" or len(pending) != 2:
            raise FileAgentError("固定响应演示未完成")
        # Only this isolated fixture supplies preselected approval strings.
        # Real --apply / --undo always reads the user's exact phrase from stdin.
        for item in pending:
            manager.apply(item["id"], "APPROVE " + item["id"])
        print(f"[fixture] approved: moved={(root / 'sorted/notes.txt').exists()}; deleted={not (root / 'trash.txt').exists()}")
        manager = FileManager(root)  # Discard the first application object.
        manager.undo(pending[-1]["id"], "UNDO " + pending[-1]["id"])
        manager = FileManager(root)
        manager.undo(pending[0]["id"], "UNDO " + pending[0]["id"])
        restored = (root / "notes.txt").read_text() == "keep this note\n" and (root / "trash.txt").read_text() == "recover this delete\n"
        print(f"[fixture] reopened journal: delete_undo=True; move_undo=True; bytes_restored={restored}")
        if not restored:
            raise FileAgentError("内容恢复失败")
        print("[fixture] temporary workspace cleaned on exit; no live model called")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--queue", choices=["move", "copy", "delete"])
    actions.add_argument("--apply", metavar="ID")
    actions.add_argument("--undo", metavar="ID")
    actions.add_argument("--cancel", metavar="ID")
    actions.add_argument("--status", action="store_true")
    actions.add_argument("--live", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--destination")
    parser.add_argument("--task")
    args = parser.parse_args(argv)
    try:
        if args.workspace is None:
            if any((args.queue, args.apply, args.undo, args.cancel, args.status, args.live, args.task, args.source, args.destination)):
                parser.error("操作需要明确的 --workspace；无参数只演示临时 fixture")
            asyncio.run(fixture_demo())
            return 0
        if (args.source is not None or args.destination is not None) and not args.queue:
            parser.error("--source/--destination 只能与 --queue 一起使用")
        manager = FileManager(args.workspace)
        if args.live:
            if not args.task:
                parser.error("--live 需要 --task")
            result = asyncio.run(propose_with_model(manager, args.task, live=True))
            print(json.dumps({"planning_status": result.status, "model_text": result.text,
                              "executed": False, "pending": manager.preview()}, ensure_ascii=False, indent=2))
            return 0 if result.status == "complete" else 1
        if args.task:
            parser.error("--task 仅用于 --live；无参数演示固定响应")
        if args.queue:
            if not args.source:
                parser.error("--queue 需要 --source")
            value = manager.queue(args.queue, args.source, args.destination)
        elif args.apply or args.undo:
            operation_id = args.apply or args.undo
            verb = "APPROVE" if args.apply else "UNDO"
            print(json.dumps(manager.history(), ensure_ascii=False, indent=2))
            approval = input(f"输入 {verb} {operation_id}，其他输入均拒绝：")
            value = manager.apply(operation_id, approval) if args.apply else manager.undo(operation_id, approval)
        elif args.cancel:
            value = manager.cancel(args.cancel)
        else:
            value = {"pending": manager.preview(), "history": manager.history()}
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, sqlite3.Error, OSError, EOFError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
