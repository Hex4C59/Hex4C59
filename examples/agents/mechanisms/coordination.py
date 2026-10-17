"""Durable local approval and coordination; caller identities are host supplied."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import time
from typing import Callable
import uuid


class CoordinationError(ValueError):
    """A request, ownership proof, version or cursor does not match."""


def _json(value) -> str:
    # Reject ambiguous object keys and non-JSON values before hashing/storing.
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise CoordinationError("JSON object keys must be strings")
            for v in item.values():
                check(v)
        elif isinstance(item, list):
            for v in item:
                check(v)
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise CoordinationError("Only JSON values are supported")
    check(value)
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise CoordinationError("Invalid JSON value") from exc


def _name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoordinationError("Identity/ID must be nonempty")
    return value


def _version(value: int):
    if type(value) is not int or value < 0:
        raise CoordinationError("Version must be a nonnegative integer")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.parent.is_dir() or self.path.is_symlink():
            raise CoordinationError("Use a database in an existing private local directory")
        with self._transaction() as conn:
            for statement in (
                """CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY, actor TEXT NOT NULL, payload TEXT NOT NULL,
                    digest TEXT NOT NULL, expires REAL NOT NULL, binding TEXT NOT NULL,
                    state TEXT NOT NULL, token TEXT, result TEXT)""",
                """CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, description TEXT NOT NULL, dependencies TEXT NOT NULL,
                    state TEXT NOT NULL, owner TEXT, version INTEGER NOT NULL, token TEXT, result TEXT)""",
                """CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL,
                    recipient TEXT, content TEXT NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS cursors (
                    consumer TEXT PRIMARY KEY, actor TEXT NOT NULL, position INTEGER NOT NULL,
                    token TEXT, through INTEGER, message_ids TEXT)""",
            ):
                conn.execute(statement)

    @contextmanager
    def _transaction(self):
        # No await or external work inside the transaction. Separate connections
        # let independent app invocations contend on SQLite's actual lock.
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _get(conn, table: str, key: str, value: str) -> dict:
        # table/key are only fixed literals at the call sites, never model input.
        row = conn.execute(f"SELECT * FROM {table} WHERE {key}=?", (value,)).fetchone()
        if row is None:
            raise CoordinationError("Unknown ID")
        return dict(row)


class ApprovalInbox(_Database):
    """Host supplies actor identity and allowlist; this is not a login service."""
    def __init__(self, path: Path, *, authorized_actors: set[str], clock: Callable[[], float] = time.time):
        self.authorized_actors = frozenset(_name(a) for a in authorized_actors)
        self.clock = clock
        super().__init__(path)

    def _authorized(self, actor: str):
        if actor not in self.authorized_actors:
            raise CoordinationError("Actor is not authorized by the trusted caller")

    def _now(self) -> float:
        value = float(self.clock())
        if not math.isfinite(value):
            raise CoordinationError("Invalid clock")
        return value

    @staticmethod
    def _view(row: dict) -> dict:
        return {"id": row["id"], "actor": row["actor"], "payload": json.loads(row["payload"]),
                "payload_digest": row["digest"], "expires_at": row["expires"],
                "binding": row["binding"], "state": row["state"],
                "result": json.loads(row["result"]) if row["result"] is not None else None}

    def request(self, payload: dict, *, actor: str, ttl_seconds: float = 3600) -> dict:
        self._authorized(actor)
        if not isinstance(payload, dict):
            raise CoordinationError("Request payload must be a JSON object")
        if not isinstance(ttl_seconds, (int, float)) or not math.isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise CoordinationError("Expiry must be a positive finite interval")
        body = _json(payload)
        operation_id = uuid.uuid4().hex
        expires = self._now() + ttl_seconds
        if not math.isfinite(expires):
            raise CoordinationError("Invalid expiry")
        digest = _digest(body)
        binding = _digest(_json({"id": operation_id, "actor": actor, "digest": digest, "expires_at": expires}))
        with self._transaction() as conn:
            conn.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,'pending',NULL,NULL)",
                         (operation_id, actor, body, digest, expires, binding))
            return self._view(self._get(conn, "approvals", "id", operation_id))

    def get(self, request_id: str) -> dict:
        with self._transaction() as conn:
            return self._view(self._get(conn, "approvals", "id", request_id))

    def list_requests(self, *, actor: str) -> list[dict]:
        self._authorized(actor)
        with self._transaction() as conn:
            return [self._view(dict(row)) for row in conn.execute(
                "SELECT * FROM approvals WHERE actor=? ORDER BY rowid", (actor,))]

    def _matching(self, conn, request_id, actor, payload, binding) -> dict:
        self._authorized(actor)
        row = self._get(conn, "approvals", "id", request_id)
        expected = _digest(_json({"id": row["id"], "actor": row["actor"],
                                 "digest": row["digest"], "expires_at": row["expires"]}))
        if (actor != row["actor"] or binding != row["binding"] or row["binding"] != expected
                or _digest(row["payload"]) != row["digest"] or _digest(_json(payload)) != row["digest"]):
            raise CoordinationError("Request ID/actor/body/expiry binding does not match")
        if self._now() >= row["expires"]:
            raise CoordinationError("Request expired; no decision or claim granted")
        return row

    def decide(self, request_id: str, *, actor: str, payload: dict, binding: str, approve: bool) -> dict:
        if type(approve) is not bool:
            raise CoordinationError("Decision must be an explicit boolean")
        with self._transaction() as conn:
            row = self._matching(conn, request_id, actor, payload, binding)
            if row["state"] != "pending":
                raise CoordinationError("Request already decided or claimed")
            conn.execute("UPDATE approvals SET state=? WHERE id=? AND state='pending'",
                         ("approved" if approve else "rejected", request_id))
            return self._view(self._get(conn, "approvals", "id", request_id))

    def claim(self, request_id: str, *, actor: str, payload: dict, binding: str) -> dict:
        with self._transaction() as conn:
            row = self._matching(conn, request_id, actor, payload, binding)
            if row["state"] != "approved":
                raise CoordinationError("Only an unclaimed approved request can be claimed")
            token = uuid.uuid4().hex
            conn.execute("UPDATE approvals SET state='claimed', token=? WHERE id=? AND state='approved'",
                         (token, request_id))
            return self._view(self._get(conn, "approvals", "id", request_id)) | {"token": token}

    def finish(self, request_id: str, *, actor: str, token: str, result) -> dict:
        self._authorized(actor)
        with self._transaction() as conn:
            row = self._get(conn, "approvals", "id", request_id)
            if row["state"] != "claimed" or actor != row["actor"] or token != row["token"]:
                raise CoordinationError("Claim owner/token does not match, or already finished")
            conn.execute("UPDATE approvals SET state='finished', result=? WHERE id=?", (_json(result), request_id))
            return self._view(self._get(conn, "approvals", "id", request_id))


class TaskBoard(_Database):
    """Atomic ownership/version transitions and acknowledged per-consumer mail."""
    @staticmethod
    def _view(row: dict) -> dict:
        return {"id": row["id"], "description": row["description"],
                "depends_on": json.loads(row["dependencies"]), "state": row["state"],
                "owner": row["owner"], "version": row["version"],
                "result": json.loads(row["result"]) if row["result"] is not None else None}

    def add_task(self, task_id: str, description: str, *, depends_on=()) -> dict:
        _name(task_id)
        _name(description)
        dependencies = list(depends_on)
        for item in dependencies:
            _name(item)
        if len(set(dependencies)) != len(dependencies) or task_id in dependencies:
            raise CoordinationError("Invalid dependencies")
        with self._transaction() as conn:
            for item in dependencies:
                self._get(conn, "tasks", "id", item)  # References must already exist: no dependency cycles.
            try:
                conn.execute("INSERT INTO tasks VALUES (?,?,?,'pending',NULL,0,NULL,NULL)",
                             (task_id, description, _json(dependencies)))
            except sqlite3.IntegrityError as exc:
                raise CoordinationError("Task ID already exists") from exc
            return self._view(self._get(conn, "tasks", "id", task_id))

    def get_task(self, task_id: str) -> dict:
        with self._transaction() as conn:
            return self._view(self._get(conn, "tasks", "id", task_id))

    def claim_task(self, task_id: str, *, actor: str, version: int) -> dict:
        _name(actor)
        _version(version)
        with self._transaction() as conn:
            row = self._get(conn, "tasks", "id", task_id)
            if row["state"] != "pending" or row["version"] != version:
                raise CoordinationError("Task already claimed or stale version")
            if any(self._get(conn, "tasks", "id", d)["state"] != "completed" for d in json.loads(row["dependencies"])):
                raise CoordinationError("Dependencies are not complete")
            token = uuid.uuid4().hex
            changed = conn.execute("""UPDATE tasks SET state='claimed', owner=?, token=?, version=version+1
                WHERE id=? AND version=? AND state='pending'""", (actor, token, task_id, version)).rowcount
            if changed != 1:
                raise CoordinationError("Concurrent task change")
            return self._view(self._get(conn, "tasks", "id", task_id)) | {"token": token}

    def _transition(self, task_id, actor, version, token, *, release, result=None):
        _version(version)
        with self._transaction() as conn:
            row = self._get(conn, "tasks", "id", task_id)
            if (row["state"] != "claimed" or row["owner"] != actor
                    or row["version"] != version or row["token"] != token):
                raise CoordinationError("Task owner/token/version does not match")
            changed = conn.execute("""UPDATE tasks SET state=?, owner=?, token=NULL, result=?, version=version+1
                WHERE id=? AND owner=? AND version=? AND token=? AND state='claimed'""",
                ("pending" if release else "completed", None if release else actor,
                 None if release else _json(result), task_id, actor, version, token)).rowcount
            if changed != 1:
                raise CoordinationError("Concurrent task change")
            return self._view(self._get(conn, "tasks", "id", task_id))

    def complete_task(self, task_id: str, *, actor: str, version: int, token: str, result) -> dict:
        return self._transition(task_id, actor, version, token, release=False, result=result)

    def release_task(self, task_id: str, *, actor: str, version: int, token: str) -> dict:
        return self._transition(task_id, actor, version, token, release=True)

    def post_message(self, *, sender: str, recipient: str | None, content: str) -> int:
        _name(sender)
        if recipient is not None:
            _name(recipient)
        _name(content)
        with self._transaction() as conn:
            return conn.execute("INSERT INTO messages(sender,recipient,content) VALUES (?,?,?)",
                                (sender, recipient, content)).lastrowid

    def poll_messages(self, consumer: str, *, actor: str, limit: int = 20) -> dict:
        _name(consumer)
        _name(actor)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise CoordinationError("Message limit must be between 1 and 100")
        with self._transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO cursors VALUES (?,?,0,NULL,NULL,NULL)", (consumer, actor))
            row = self._get(conn, "cursors", "consumer", consumer)
            if row["actor"] != actor:
                raise CoordinationError("Consumer belongs to a different actor")
            if row["token"] is None:
                messages = [dict(m) for m in conn.execute("""SELECT * FROM messages
                    WHERE id>? AND (recipient IS NULL OR recipient=?) ORDER BY id LIMIT ?""",
                    (row["position"], actor, limit))]
                if not messages:
                    return {"token": None, "after": row["position"], "through": row["position"], "messages": []}
                row.update(token=uuid.uuid4().hex, through=messages[-1]["id"],
                           message_ids=_json([m["id"] for m in messages]))
                conn.execute("UPDATE cursors SET token=?, through=?, message_ids=? WHERE consumer=?",
                             (row["token"], row["through"], row["message_ids"], consumer))
            else:
                ids = json.loads(row["message_ids"])
                messages = [self._get(conn, "messages", "id", message_id) for message_id in ids]
            return {"token": row["token"], "after": row["position"], "through": row["through"], "messages": messages}

    def ack_messages(self, consumer: str, *, actor: str, token: str) -> int:
        with self._transaction() as conn:
            row = self._get(conn, "cursors", "consumer", consumer)
            if row["actor"] != actor or not token or token != row["token"]:
                raise CoordinationError("Message batch/consumer does not match or was already acknowledged")
            conn.execute("UPDATE cursors SET position=?, token=NULL, through=NULL, message_ids=NULL WHERE consumer=?",
                         (row["through"], consumer))
            return row["through"]


async def demo() -> dict:
    """Real local SQLite checks. Host app labels this as an offline fixture."""
    with tempfile.TemporaryDirectory(prefix="coordination-fixture-") as directory:
        db = Path(directory) / "coordination.sqlite3"
        payload = {"action": "prepare_draft", "parameters": {"name": "synthetic-note"}}
        inbox = ApprovalInbox(db, authorized_actors={"local-user"})
        request = inbox.request(payload, actor="local-user")
        inbox = ApprovalInbox(db, authorized_actors={"local-user"})
        assert inbox.get(request["id"])["state"] == "pending"
        kwargs = {"actor": "local-user", "payload": payload, "binding": request["binding"]}
        inbox.decide(request["id"], **kwargs, approve=True)
        claim = inbox.claim(request["id"], **kwargs)
        inbox = ApprovalInbox(db, authorized_actors={"local-user"})
        try:
            inbox.claim(request["id"], **kwargs)
        except CoordinationError:
            pass
        else:
            raise AssertionError("Claim repeated")
        inbox.finish(request["id"], actor="local-user", token=claim["token"], result={"draft": "synthetic"})
        assert inbox.get(request["id"])["state"] == "finished"
        board = TaskBoard(db)
        task = board.add_task("review", "Review synthetic draft")
        owned = board.claim_task(task["id"], actor="worker-a", version=task["version"])
        board = TaskBoard(db)
        board.complete_task(task["id"], actor="worker-a", version=owned["version"], token=owned["token"], result="checked")
        assert board.get_task(task["id"])["state"] == "completed"
        other = board.post_message(sender="lead", recipient="worker-b", content="B only")
        direct = board.post_message(sender="lead", recipient="worker-a", content="A only")
        broadcast = board.post_message(sender="lead", recipient=None, content="all workers")
        batch = board.poll_messages("worker-a-inbox", actor="worker-a", limit=1)
        assert [m["id"] for m in batch["messages"]] == [direct]
        board = TaskBoard(db)
        assert board.poll_messages("worker-a-inbox", actor="worker-a") == batch
        board.ack_messages("worker-a-inbox", actor="worker-a", token=batch["token"])
        batch2 = board.poll_messages("worker-a-inbox", actor="worker-a")
        assert [m["id"] for m in batch2["messages"]] == [broadcast]
        board.ack_messages("worker-a-inbox", actor="worker-a", token=batch2["token"])
        assert not board.poll_messages("worker-a-inbox", actor="worker-a")["messages"]
        assert [m["id"] for m in board.poll_messages("worker-b-inbox", actor="worker-b")["messages"]] == [other, broadcast]
        return {"ok": True, "approval_reopen": True, "one_shot_claim": True,
                "versioned_task": True, "acknowledged_cursor": True, "recipient_isolation": True}
