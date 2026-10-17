"""Real SQLite state, restart, races and cursor boundaries; no model calls."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from coordination import ApprovalInbox, CoordinationError, TaskBoard, demo


class CoordinationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordination-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite3"
        self.now = 1000.0
        self.body = {"action": "draft", "parameters": {"name": "synthetic", "count": 2}}
        self.inbox = self.reopen()
        self.board = TaskBoard(self.path)

    def reopen(self, actors=None):
        return ApprovalInbox(self.path, authorized_actors=actors if actors is not None else {"alice", "bob"},
                             clock=lambda: self.now)

    def request(self):
        return self.inbox.request(self.body, actor="alice", ttl_seconds=10)

    def args(self, request):
        return {"actor": "alice", "payload": self.body, "binding": request["binding"]}

    def race(self, functions):
        barrier = threading.Barrier(len(functions))
        def invoke(fn):
            barrier.wait(timeout=10)
            try:
                return (True, fn())
            except CoordinationError as exc:
                return (False, str(exc))
        with ThreadPoolExecutor(max_workers=len(functions)) as pool:
            return list(pool.map(invoke, functions))

    def test_pending_and_decision_survive_new_os_process(self):
        # Wall-clock expiry here, as a separate process has its own clock.
        inbox = ApprovalInbox(self.path, authorized_actors={"alice"})
        request = inbox.request(self.body, actor="alice")
        self.assertEqual(self.reopen().get(request["id"])["state"], "pending")
        code = """import json,sys
from pathlib import Path
from coordination import ApprovalInbox
path, request_id, body, binding = sys.argv[1:]
inbox = ApprovalInbox(Path(path), authorized_actors={'alice'})
kwargs = dict(actor='alice', payload=json.loads(body), binding=binding)
inbox.decide(request_id, **kwargs, approve=True)
print(json.dumps(inbox.claim(request_id, **kwargs)))
"""
        result = subprocess.run([sys.executable, "-c", code, str(self.path), request["id"], json.dumps(self.body), request["binding"]],
                                cwd=Path(__file__).parent, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claim = json.loads(result.stdout)
        reopened = ApprovalInbox(self.path, authorized_actors={"alice"})
        self.assertEqual(reopened.get(request["id"])["state"], "claimed")
        with self.assertRaises(CoordinationError):
            reopened.claim(request["id"], **self.args(request))
        reopened.finish(request["id"], actor="alice", token=claim["token"], result={"draft": "saved"})
        self.assertEqual(self.reopen().get(request["id"])["result"], {"draft": "saved"})

    def test_restart_discovers_requests_without_in_memory_ids(self):
        request = self.request()
        self.inbox.request({"action": "other"}, actor="bob")
        self.assertEqual([r["id"] for r in self.reopen().list_requests(actor="alice")], [request["id"]])
        with self.assertRaises(CoordinationError):
            self.reopen({"bob"}).list_requests(actor="alice")

    def test_request_identity_actor_body_and_binding_must_all_match(self):
        request = self.request()
        other = self.request()
        cases = [
            ("missing-id", self.args(request)),
            (other["id"], self.args(request)),
            (request["id"], self.args(request) | {"actor": "bob"}),
            (request["id"], self.args(request) | {"actor": "model-invented-user"}),
            (request["id"], self.args(request) | {"payload": {"action": "send"}}),
            (request["id"], self.args(request) | {"binding": "different-expiry-binding"}),
        ]
        for request_id, args in cases:
            with self.subTest(request_id=request_id, args=args), self.assertRaises(CoordinationError):
                self.inbox.decide(request_id, **args, approve=True)
        self.assertEqual(self.reopen().get(request["id"])["state"], "pending")
        self.assertEqual(self.reopen().get(other["id"])["state"], "pending")
        self.inbox.decide(request["id"], **self.args(request), approve=True)
        for request_id, args in cases:
            with self.subTest(claim_id=request_id, args=args), self.assertRaises(CoordinationError):
                self.reopen().claim(request_id, **args)
        self.assertEqual(self.reopen().get(request["id"])["state"], "approved")

    def test_revoking_trusted_caller_authorization_prevents_decision_and_claim(self):
        request = self.request()
        with self.assertRaises(CoordinationError):
            self.reopen({"bob"}).decide(request["id"], **self.args(request), approve=True)
        self.inbox.decide(request["id"], **self.args(request), approve=True)
        with self.assertRaises(CoordinationError):
            self.reopen({"bob"}).claim(request["id"], **self.args(request))

    def test_expiry_is_bound_and_checked_at_decision_and_claim(self):
        request = self.request()
        self.now = request["expires_at"]
        with self.assertRaises(CoordinationError):
            self.inbox.decide(request["id"], **self.args(request), approve=True)
        self.assertEqual(self.inbox.get(request["id"])["state"], "pending")
        request = self.request()
        self.inbox.decide(request["id"], **self.args(request), approve=True)
        self.now += 10
        with self.assertRaises(CoordinationError):
            self.reopen().claim(request["id"], **self.args(request))
        self.assertEqual(self.inbox.get(request["id"])["state"], "approved")

    def test_altering_persisted_expiry_or_body_invalidates_binding(self):
        for field, value in (("expires", 9000.0), ("payload", '{"action":"changed"}')):
            request = self.request()
            with sqlite3.connect(self.path) as conn:
                conn.execute(f"UPDATE approvals SET {field}=? WHERE id=?", (value, request["id"]))
            with self.subTest(field=field), self.assertRaises(CoordinationError):
                self.inbox.decide(request["id"], **self.args(request), approve=True)

    def test_decision_rejection_and_claim_are_one_shot(self):
        request = self.request()
        with self.assertRaises(CoordinationError):
            self.inbox.claim(request["id"], **self.args(request))
        self.inbox.decide(request["id"], **self.args(request), approve=False)
        for approve in (True, False):
            with self.assertRaises(CoordinationError):
                self.reopen().decide(request["id"], **self.args(request), approve=approve)
        with self.assertRaises(CoordinationError):
            self.inbox.claim(request["id"], **self.args(request))
        approved = self.request()
        self.inbox.decide(approved["id"], **self.args(approved), approve=True)
        claim = self.inbox.claim(approved["id"], **self.args(approved))
        with self.assertRaises(CoordinationError):
            self.reopen().claim(approved["id"], **self.args(approved))
        for actor, token in (("bob", claim["token"]), ("alice", "wrong-token")):
            with self.assertRaises(CoordinationError):
                self.inbox.finish(approved["id"], actor=actor, token=token, result="wrong")
        self.now += 100  # Finishing an already-issued claim is allowed after expiry.
        self.inbox.finish(approved["id"], actor="alice", token=claim["token"], result="done")
        with self.assertRaises(CoordinationError):
            self.inbox.finish(approved["id"], actor="alice", token=claim["token"], result="overwrite")
        self.assertEqual(self.reopen().get(approved["id"])["result"], "done")

    def test_json_key_order_is_irrelevant_but_invalid_json_is_rejected(self):
        request = self.request()
        reordered = {"parameters": {"count": 2, "name": "synthetic"}, "action": "draft"}
        self.inbox.decide(request["id"], **(self.args(request) | {"payload": reordered}), approve=True)
        for body in ({1: "not a JSON object key"}, {"value": float("nan")}, {"tuple": (1, 2)}):
            with self.assertRaises(CoordinationError):
                self.inbox.request(body, actor="alice")
        for ttl in (0, -1, float("inf"), float("nan")):
            with self.assertRaises(CoordinationError):
                self.inbox.request({}, actor="alice", ttl_seconds=ttl)
        with self.assertRaises(CoordinationError):
            self.inbox.decide(request["id"], **self.args(request), approve="yes")

    def test_real_sql_abort_rolls_back_decision_then_allows_retry(self):
        request = self.request()
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TRIGGER abort_decision BEFORE UPDATE ON approvals BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.inbox.decide(request["id"], **self.args(request), approve=True)
        self.assertEqual(self.reopen().get(request["id"])["state"], "pending")
        with sqlite3.connect(self.path) as conn:
            conn.execute("DROP TRIGGER abort_decision")
        self.inbox.decide(request["id"], **self.args(request), approve=True)
        self.assertEqual(self.reopen().get(request["id"])["state"], "approved")

    def test_concurrent_decisions_and_claims_have_one_winner(self):
        request = self.request()
        results = self.race([lambda: self.reopen().decide(request["id"], **self.args(request), approve=True) for _ in range(2)])
        self.assertEqual(sum(ok for ok, _ in results), 1)
        results = self.race([lambda: self.reopen().claim(request["id"], **self.args(request)) for _ in range(2)])
        self.assertEqual(sum(ok for ok, _ in results), 1)
        self.assertEqual(self.reopen().get(request["id"])["state"], "claimed")

    def test_concurrent_task_claims_and_completions_cannot_overwrite(self):
        task = self.board.add_task("task", "synthetic review")
        results = self.race([lambda actor=actor: TaskBoard(self.path).claim_task("task", actor=actor, version=task["version"])
                             for actor in ("worker-a", "worker-b")])
        winners = [value for ok, value in results if ok]
        self.assertEqual(len(winners), 1)
        claim = winners[0]
        args = {"actor": claim["owner"], "version": claim["version"], "token": claim["token"]}
        results = self.race([lambda result=result: TaskBoard(self.path).complete_task("task", **args, result=result)
                             for result in ("first result", "second result")])
        self.assertEqual(sum(ok for ok, _ in results), 1)
        expected = next(value["result"] for ok, value in results if ok)
        self.assertEqual(TaskBoard(self.path).get_task("task")["result"], expected)
        self.assertEqual(TaskBoard(self.path).get_task("task")["version"], 2)

    def test_independent_processes_race_for_same_task_and_restart_completion(self):
        self.board.add_task("race", "single owner")
        code = """import json,sys
from pathlib import Path
from coordination import TaskBoard, CoordinationError
board = TaskBoard(Path(sys.argv[1]))
try:
    value = board.claim_task('race', actor=sys.argv[2], version=0)
except CoordinationError:
    print('{}')
else:
    print(json.dumps(value))
"""
        processes = [subprocess.Popen([sys.executable, "-c", code, str(self.path), actor],
                                      cwd=Path(__file__).parent, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for actor in ("process-a", "process-b")]
        replies = []
        try:
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stderr)
                replies.append(json.loads(stdout))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        winners = [r for r in replies if r]
        self.assertEqual(len(winners), 1)
        owned = winners[0]
        self.assertEqual(TaskBoard(self.path).get_task("race")["owner"], owned["owner"])
        TaskBoard(self.path).complete_task("race", actor=owned["owner"], version=owned["version"],
                                           token=owned["token"], result="winner only")
        self.assertEqual(TaskBoard(self.path).get_task("race")["result"], "winner only")

    def test_task_ownership_release_and_stale_versions(self):
        self.board.add_task("task", "synthetic review")
        for version in (False, -1, 0.0):
            with self.assertRaises(CoordinationError):
                self.board.claim_task("task", actor="worker-a", version=version)
        claim = self.board.claim_task("task", actor="worker-a", version=0)
        args = {"actor": "worker-a", "version": 1, "token": claim["token"]}
        for replacement in ({"actor": "worker-b"}, {"version": 0}, {"token": "wrong"}):
            with self.assertRaises(CoordinationError):
                TaskBoard(self.path).complete_task("task", **(args | replacement), result="bad")
        pending = self.board.release_task("task", **args)
        self.assertEqual(pending["version"], 2)
        with self.assertRaises(CoordinationError):
            self.board.claim_task("task", actor="worker-b", version=0)
        current = self.board.claim_task("task", actor="worker-b", version=2)
        with self.assertRaises(CoordinationError):
            self.board.complete_task("task", **args, result="stale owner")
        self.board.complete_task("task", actor="worker-b", version=current["version"], token=current["token"], result="valid")
        self.assertEqual(TaskBoard(self.path).get_task("task")["result"], "valid")

    def test_dependencies_and_duplicate_ids_do_not_erase_tasks(self):
        self.board.add_task("build", "build synthetic data")
        self.board.add_task("review", "review data", depends_on=["build"])
        with self.assertRaises(CoordinationError):
            self.board.claim_task("review", actor="worker-a", version=0)
        with self.assertRaises(CoordinationError):
            self.board.add_task("build", "overwrite description")
        with self.assertRaises(CoordinationError):
            self.board.add_task("missing", "bad dependency", depends_on=["unknown"])
        claim = self.board.claim_task("build", actor="worker-a", version=0)
        self.board.complete_task("build", actor="worker-a", version=claim["version"], token=claim["token"], result="built")
        self.assertEqual(self.board.claim_task("review", actor="worker-b", version=0)["state"], "claimed")
        self.assertEqual(self.board.get_task("build")["description"], "build synthetic data")

    def test_cursor_limit_filters_before_advancing_and_isolates_consumers(self):
        b1 = self.board.post_message(sender="lead", recipient="bob", content="b1")
        a1 = self.board.post_message(sender="lead", recipient="alice", content="a1")
        b2 = self.board.post_message(sender="lead", recipient="bob", content="b2")
        a2 = self.board.post_message(sender="lead", recipient="alice", content="a2")
        all_id = self.board.post_message(sender="lead", recipient=None, content="broadcast")
        received = []
        for expected in (a1, a2, all_id):
            batch = TaskBoard(self.path).poll_messages("a", actor="alice", limit=1)
            self.assertEqual([m["id"] for m in batch["messages"]], [expected])
            received.extend(m["id"] for m in batch["messages"])
            self.assertEqual(TaskBoard(self.path).ack_messages("a", actor="alice", token=batch["token"]), expected)
        self.assertEqual(received, [a1, a2, all_id])
        self.assertEqual(self.board.poll_messages("a", actor="alice")["messages"], [])
        self.assertEqual([m["id"] for m in self.board.poll_messages("b", actor="bob")["messages"]], [b1, b2, all_id])

    def test_unacked_batch_survives_restart_and_new_messages_wait(self):
        first = self.board.post_message(sender="lead", recipient="alice", content="first")
        batch = self.board.poll_messages("a", actor="alice")
        second = self.board.post_message(sender="lead", recipient="alice", content="second")
        self.assertEqual(TaskBoard(self.path).poll_messages("a", actor="alice", limit=1), batch)
        self.assertEqual([m["id"] for m in batch["messages"]], [first])
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TRIGGER abort_ack BEFORE UPDATE ON cursors BEGIN SELECT RAISE(ABORT, 'injected ack failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.board.ack_messages("a", actor="alice", token=batch["token"])
        self.assertEqual(TaskBoard(self.path).poll_messages("a", actor="alice"), batch)
        with sqlite3.connect(self.path) as conn:
            conn.execute("DROP TRIGGER abort_ack")
        self.board.ack_messages("a", actor="alice", token=batch["token"])
        self.assertEqual([m["id"] for m in self.board.poll_messages("a", actor="alice")["messages"]], [second])

    def test_cursor_identity_token_repeat_ack_and_empty_edges(self):
        empty = self.board.poll_messages("a", actor="alice")
        self.assertIsNone(empty["token"])
        self.assertEqual(empty["through"], 0)
        with self.assertRaises(CoordinationError):
            self.board.ack_messages("a", actor="alice", token="")
        self.board.post_message(sender="lead", recipient="alice", content="later")
        batch = self.board.poll_messages("a", actor="alice")
        for actor, token in (("bob", batch["token"]), ("alice", "skip-to-999")):
            with self.assertRaises(CoordinationError):
                self.board.ack_messages("a", actor=actor, token=token)
        with self.assertRaises(CoordinationError):
            self.board.poll_messages("a", actor="bob")
        results = self.race([lambda: TaskBoard(self.path).ack_messages("a", actor="alice", token=batch["token"]) for _ in range(2)])
        self.assertEqual(sum(ok for ok, _ in results), 1)
        with self.assertRaises(CoordinationError):
            self.board.ack_messages("a", actor="alice", token=batch["token"])
        self.assertEqual(self.board.poll_messages("a", actor="alice")["messages"], [])
        for limit in (0, -1, 101, True):
            with self.assertRaises(CoordinationError):
                self.board.poll_messages("a", actor="alice", limit=limit)

    def test_demo_uses_real_temporary_sqlite_and_returns_checks(self):
        result = asyncio.run(demo())
        self.assertTrue(result["ok"])
        self.assertTrue(all(result.values()))


if __name__ == "__main__":
    unittest.main()
