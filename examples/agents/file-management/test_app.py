"""Integration tests mutate only synthetic temporary workspaces."""
import asyncio
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import app
from agent_runtime import ScriptedModel, run_agent


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="file-agent-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "work"
        self.root.mkdir()
        (self.root / "sorted").mkdir()
        self.original = b"synthetic bytes\x00\xff\n"
        (self.root / "note.txt").write_bytes(self.original)
        self.manager = app.FileManager(self.root)

    def queue(self, action="move", source="note.txt", destination="sorted/note.txt"):
        return self.manager.queue(action, source, None if action == "delete" else destination)["id"]

    def approve(self, operation_id):
        return self.manager.apply(operation_id, "APPROVE " + operation_id)

    def undo(self, operation_id):
        return self.manager.undo(operation_id, "UNDO " + operation_id)

    def child(self, *arguments, input=None):
        return subprocess.run([sys.executable, str(Path(app.__file__)), "--workspace", str(self.root), *arguments],
                              input=input, text=True, capture_output=True, timeout=20)

    def crash(self, point, *, undo=False, action="move"):
        operation_id = self.queue("delete" if undo else action)
        if undo:
            self.approve(operation_id)
        code = """import os, sys
from pathlib import Path
from app import FileManager
root, operation_id, point, mode = sys.argv[1:]
def stop(where, row):
    if where == point:
        os._exit(73)
manager = FileManager(Path(root), fault=stop)
if mode == 'undo':
    manager.undo(operation_id, 'UNDO ' + operation_id)
else:
    manager.apply(operation_id, 'APPROVE ' + operation_id)
"""
        result = subprocess.run([sys.executable, "-c", code, str(self.root), operation_id, point,
                                 "undo" if undo else "apply"], cwd=Path(app.__file__).parent,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 73, result.stderr)
        return operation_id

    def test_dry_run_denial_and_cancel_change_no_business_file(self):
        operation_id = self.queue("delete")
        self.assertEqual(len(self.manager.preview()), 1)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        with self.assertRaises(app.FileAgentError):
            self.manager.apply(operation_id, "y")
        with self.assertRaises(app.FileAgentError):
            self.manager.apply(operation_id, "APPROVE another-id")
        self.manager.cancel(operation_id)
        self.manager = app.FileManager(self.root)
        self.assertEqual(self.manager.preview(), [])
        self.assertEqual(self.manager.history()[0]["state"], "cancelled")
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        with self.assertRaises(app.FileAgentError):
            self.approve(operation_id)

    def test_move_reconstruct_and_undo_preserves_bytes(self):
        operation_id = self.queue()
        self.approve(operation_id)
        self.assertFalse((self.root / "note.txt").exists())
        self.assertEqual((self.root / "sorted/note.txt").read_bytes(), self.original)
        self.manager = app.FileManager(self.root)
        self.undo(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertFalse((self.root / "sorted/note.txt").exists())
        self.assertEqual(self.manager.history()[0]["state"], "undone")

    def test_delete_snapshot_survives_new_application_invocations(self):
        operation_id = self.queue("delete")
        denied = self.child("--apply", operation_id, input="n\n")
        self.assertNotEqual(denied.returncode, 0)
        self.assertTrue((self.root / "note.txt").exists())
        applied = self.child("--apply", operation_id, input="APPROVE " + operation_id + "\n")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertFalse((self.root / "note.txt").exists())
        with sqlite3.connect(self.root / app.STATE_DIR / "journal.sqlite3") as conn:
            self.assertEqual(conn.execute("SELECT image FROM operations WHERE id=?", (operation_id,)).fetchone()[0], self.original)
        undone = self.child("--undo", operation_id, input="UNDO " + operation_id + "\n")
        self.assertEqual(undone.returncode, 0, undone.stdout + undone.stderr)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_copy_undo_removes_only_unchanged_copy(self):
        operation_id = self.queue("copy")
        self.approve(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.manager = app.FileManager(self.root)
        self.undo(operation_id)
        self.assertFalse((self.root / "sorted/note.txt").exists())
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_move_chain_undo_updates_previous_file_identity(self):
        first = self.queue()
        self.approve(first)
        second = self.queue("move", "sorted/note.txt", "last.txt")
        self.approve(second)
        with self.assertRaises(app.FileAgentError):
            self.undo(first)
        self.manager = app.FileManager(self.root)
        self.undo(second)
        self.manager = app.FileManager(self.root)
        self.undo(first)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_undo_follows_execution_order_when_proposals_are_approved_in_reverse(self):
        (self.root / "other.txt").write_bytes(b"other file")
        first_queued = self.queue("delete", "note.txt")
        second_queued = self.queue("delete", "other.txt")
        self.approve(second_queued)
        self.approve(first_queued)
        self.manager = app.FileManager(self.root)
        with self.assertRaises(app.FileAgentError):
            self.undo(second_queued)
        self.undo(first_queued)
        self.manager = app.FileManager(self.root)
        self.undo(second_queued)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertEqual((self.root / "other.txt").read_bytes(), b"other file")

    def test_path_aliases_and_delete_after_move_undo_in_order(self):
        first = self.queue("move", "./note.txt", "sorted//note.txt")
        self.approve(first)
        deleted = self.queue("delete", "./sorted/note.txt")
        self.approve(deleted)
        self.manager = app.FileManager(self.root)
        self.undo(deleted)
        self.manager = app.FileManager(self.root)
        self.undo(first)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_delete_crash_after_unlink_recovers_from_database_backup(self):
        self.crash("after_source", action="delete")
        self.assertFalse((self.root / "note.txt").exists())
        self.manager = app.FileManager(self.root)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertEqual(self.manager.history()[-1]["state"], "failed")

    def test_absolute_traversal_reserved_and_symlink_paths_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "secret").write_bytes(b"outside")
        (self.root / "escape").symlink_to(outside, target_is_directory=True)
        (self.root / "inside-link").symlink_to(self.root / "note.txt")
        for path in (str(outside / "secret"), "../outside/secret", "escape/secret", "inside-link", ".file-agent/journal.sqlite3", "sorted/../note.txt"):
            with self.subTest(path=path), self.assertRaises(app.FileAgentError):
                self.manager.queue("delete", path)
        for target in ("../outside/new", "escape/new", ".file-agent/new"):
            with self.subTest(target=target), self.assertRaises(app.FileAgentError):
                self.manager.queue("move", "note.txt", target)
        self.assertEqual((outside / "secret").read_bytes(), b"outside")
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_symlink_inserted_after_preview_is_rejected(self):
        operation_id = self.queue()
        (self.root / "sorted").rmdir()
        outside = Path(self.temp.name) / "other"
        outside.mkdir()
        (self.root / "sorted").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(app.FileAgentError):
            self.approve(operation_id)
        self.assertFalse((outside / "note.txt").exists())
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_existing_destinations_and_late_conflicts_never_overwritten(self):
        destination = self.root / "sorted/note.txt"
        destination.write_bytes(b"keep existing")
        with self.assertRaises(app.FileAgentError):
            self.queue()
        destination.unlink()
        operation_id = self.queue()
        destination.write_bytes(b"late occupant")
        with self.assertRaises(app.FileAgentError):
            self.approve(operation_id)
        self.assertEqual(destination.read_bytes(), b"late occupant")
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_source_edits_after_preview_need_new_proposal(self):
        operation_id = self.queue()
        (self.root / "note.txt").write_bytes(b"edited")
        with self.assertRaises(app.FileAgentError):
            self.approve(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), b"edited")
        self.assertFalse((self.root / "sorted/note.txt").exists())

    def test_undo_refuses_occupied_original_and_edited_target(self):
        operation_id = self.queue()
        self.approve(operation_id)
        (self.root / "note.txt").write_bytes(b"new occupant")
        with self.assertRaises(app.FileAgentError):
            self.undo(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), b"new occupant")
        (self.root / "note.txt").unlink()
        (self.root / "sorted/note.txt").write_bytes(b"user edit")
        with self.assertRaises(app.FileAgentError):
            self.undo(operation_id)
        self.assertEqual((self.root / "sorted/note.txt").read_bytes(), b"user edit")

    def test_directories_hardlinks_and_oversized_files_rejected(self):
        with self.assertRaises(app.FileAgentError):
            self.manager.queue("delete", "sorted")
        os.link(self.root / "note.txt", self.root / "linked.txt")
        with self.assertRaises(app.FileAgentError):
            self.queue("delete")
        (self.root / "large").write_bytes(b"x" * (app.MAX_BYTES + 1))
        with self.assertRaises(app.FileAgentError):
            self.manager.queue("delete", "large")
        special = self.root / "special"
        special.write_bytes(b"synthetic special permissions")
        for mode in (0o4755, 0o2755):
            special.chmod(mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(app.FileAgentError):
                self.manager.queue("delete", "special")
        self.assertTrue(special.exists())

    def test_external_hardlink_added_to_target_blocks_undo(self):
        operation_id = self.queue()
        self.approve(operation_id)
        os.link(self.root / "sorted/note.txt", self.root / "external-link")
        with self.assertRaises(app.FileAgentError):
            self.undo(operation_id)
        self.assertTrue((self.root / "sorted/note.txt").exists())

    def test_journal_prepare_failure_does_not_move_file(self):
        operation_id = self.queue()
        with patch.object(self.manager, "_persist", side_effect=sqlite3.OperationalError("injected journal failure")):
            with self.assertRaises(sqlite3.Error):
                self.approve(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertFalse((self.root / "sorted/note.txt").exists())
        self.manager = app.FileManager(self.root)
        self.assertEqual(self.manager.preview()[0]["state"], "pending")

    def test_final_journal_write_failure_rolls_back_before_report(self):
        operation_id = self.queue()
        persist = self.manager._persist
        def fail_commit(conn, row, state, **kwargs):
            if state == "applied":
                raise sqlite3.OperationalError("injected final commit failure")
            return persist(conn, row, state, **kwargs)
        with patch.object(self.manager, "_persist", side_effect=fail_commit):
            with self.assertRaises(app.FileAgentError):
                self.approve(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertFalse((self.root / "sorted/note.txt").exists())
        self.manager = app.FileManager(self.root)
        self.assertEqual(self.manager.history()[0]["state"], "failed")

    def test_error_after_successful_journal_commit_keeps_committed_outcome(self):
        operation_id = self.queue()
        persist = self.manager._persist
        def report_failure(conn, row, state, **kwargs):
            persist(conn, row, state, **kwargs)
            if state == "applied":
                raise OSError("injected failure after successful commit")
        with patch.object(self.manager, "_persist", side_effect=report_failure):
            with self.assertRaises(app.RecoveryRequired):
                self.approve(operation_id)
        self.manager = app.FileManager(self.root)
        self.assertEqual(self.manager.history()[-1]["state"], "applied")
        self.assertFalse((self.root / "note.txt").exists())
        self.assertEqual((self.root / "sorted/note.txt").read_bytes(), self.original)
        self.undo(operation_id)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_corrupt_backup_is_rejected_before_delete(self):
        operation_id = self.queue("delete")
        with sqlite3.connect(self.root / app.STATE_DIR / "journal.sqlite3") as conn:
            conn.execute("UPDATE operations SET image=? WHERE id=?", (b"corrupt", operation_id))
        with self.assertRaises(app.RecoveryRequired):
            app.FileManager(self.root)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_state_directory_symlink_is_rejected(self):
        other = Path(self.temp.name) / "unmanaged"
        other.mkdir()
        root = Path(self.temp.name) / "second"
        root.mkdir()
        (root / app.STATE_DIR).symlink_to(other, target_is_directory=True)
        with self.assertRaises(app.FileAgentError):
            app.FileManager(root)
        self.assertEqual(list(other.iterdir()), [])

    def test_missing_live_credentials_fail_without_fixture_fallback(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": ""}):
            result = self.child("--live", "--task", "propose only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Live mode requires", result.stdout)
        self.assertNotIn("fixture", result.stdout)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_interrupted_apply_and_undo_recover_after_process_exit(self):
        for point in ("after_prepare", "after_target", "after_source"):
            with self.subTest(point=point):
                operation_id = self.crash(point)
                self.manager = app.FileManager(self.root)
                self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
                self.assertFalse((self.root / "sorted/note.txt").exists())
                self.assertEqual(self.manager.history()[-1]["state"], "failed")
        operation_id = self.crash("after_undo_files", undo=True)
        self.manager = app.FileManager(self.root)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertEqual(self.manager.history()[-1]["state"], "undone")

    def test_recovery_conflict_is_not_overwritten(self):
        operation_id = self.crash("after_source")
        (self.root / "note.txt").write_bytes(b"new original occupant")
        with self.assertRaises(app.RecoveryRequired):
            app.FileManager(self.root)
        self.assertEqual((self.root / "note.txt").read_bytes(), b"new original occupant")
        self.assertEqual((self.root / "sorted/note.txt").read_bytes(), self.original)
        (self.root / "note.txt").unlink()  # Explicit external resolution of our synthetic conflict.
        self.manager = app.FileManager(self.root)
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)
        self.assertEqual(self.manager.history()[-1]["state"], "failed")

    def test_concurrent_application_lock_is_refused_and_released(self):
        with self.manager._locked():
            with self.assertRaises(app.FileAgentError):
                app.FileManager(self.root)
        app.FileManager(self.root)

    def test_corrupt_journal_is_not_silently_recreated(self):
        database = self.root / app.STATE_DIR / "journal.sqlite3"
        database.write_bytes(b"not a sqlite database")
        with self.assertRaises(sqlite3.DatabaseError):
            app.FileManager(self.root)
        self.assertEqual(database.read_bytes(), b"not a sqlite database")
        self.assertEqual((self.root / "note.txt").read_bytes(), self.original)

    def test_home_and_checkout_roots_rejected(self):
        with self.assertRaises(app.FileAgentError):
            app.FileManager(Path.home())
        repo = Path(self.temp.name) / "fake-checkout"
        repo.mkdir()
        (repo / ".git").mkdir()
        child = repo / "work"
        child.mkdir()
        with self.assertRaises(app.FileAgentError):
            app.FileManager(child)
        self.assertFalse((child / app.STATE_DIR).exists())


class RuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_fixture_loop_queues_real_files_without_approving(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sorted").mkdir()
            (root / "notes.txt").write_bytes(b"notes")
            (root / "trash.txt").write_bytes(b"trash")
            manager = app.FileManager(root)
            result = await app.propose_with_model(manager, "fixture task")
            self.assertEqual(result.status, "complete")
            self.assertEqual(result.tool_calls, 2)
            self.assertEqual(len(manager.preview()), 2)
            self.assertEqual((root / "trash.txt").read_bytes(), b"trash")
            self.assertTrue((root / "notes.txt").exists())
            self.assertEqual({t.name for t in app.tools_for(manager)}, {"list_directory", "queue_operation", "preview"})

    async def test_model_cannot_approve_and_invalid_input_is_tool_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.txt").write_bytes(b"keep")
            manager = app.FileManager(root)
            model = ScriptedModel([
                {"role": "assistant", "tool_calls": [
                    app.fixture_call("apply", {"operation_id": "invented"}, "bad"),
                    app.fixture_call("queue_operation", {"action": "delete", "source": "../outside"}, "escape")]},
                {"role": "assistant", "content": "请求被拒绝。"}])
            result = await run_agent(model, "propose only", "fixture", app.tools_for(manager))
            errors = [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]
            self.assertTrue(all(not value["ok"] for value in errors))
            self.assertEqual(manager.preview(), [])
            self.assertEqual((root / "note.txt").read_bytes(), b"keep")

    async def test_live_adapter_is_closed_even_when_model_fails(self):
        class ClosedModel:
            closed = False
            async def complete(self, *_):
                raise RuntimeError("injected provider failure")
            async def aclose(self):
                self.closed = True
        model = ClosedModel()
        with tempfile.TemporaryDirectory() as directory:
            manager = app.FileManager(Path(directory))
            with patch.object(app, "model_from_env", return_value=model):
                result = await app.propose_with_model(manager, "test closure", live=True)
            self.assertEqual(result.status, "error")
            self.assertTrue(model.closed)

    async def test_default_demo_runs_real_file_tools_and_undo(self):
        output = io.StringIO()
        with redirect_stdout(output):
            await app.fixture_demo()
        self.assertIn("model=complete; pending=2", output.getvalue())
        self.assertIn("bytes_restored=True", output.getvalue())
        self.assertIn("no live model called", output.getvalue())


if __name__ == "__main__":
    unittest.main()
