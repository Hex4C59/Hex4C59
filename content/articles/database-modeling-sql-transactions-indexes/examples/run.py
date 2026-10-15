#!/usr/bin/env python3
"""Run the article's SQLite experiments in temporary, synthetic databases.

Requires Python 3.9+ and SQLite 3.37+. Uses only the standard library.
Run without -O: assertions check query results and transaction outcomes.
"""

import platform
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
BASE_TIME = 1_760_000_000
TASK_INSERT = """
    INSERT INTO tasks (id, owner_id, title, status, created_at, completed_at)
    VALUES (?, ?, ?, ?, ?, ?)
"""
TASK_QUERY = """
    SELECT id, title, created_at
    FROM tasks
    WHERE owner_id = ? AND status = 'todo'
    ORDER BY created_at DESC, id DESC
    LIMIT 20
"""


def connect(path):
    # SQL below owns BEGIN/COMMIT/ROLLBACK, rather than implicit driver transactions.
    options = {"isolation_level": None, "timeout": 0.0}
    if hasattr(sqlite3, "LEGACY_TRANSACTION_CONTROL"):
        options["autocommit"] = True
    conn = sqlite3.connect(str(path), **options)
    conn.execute("PRAGMA foreign_keys = ON")
    assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
    return conn


def create_database(conn):
    conn.executescript(SCHEMA)
    assert conn.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)


def seed_small(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.executemany(
            "INSERT INTO users (id, handle, display_name) VALUES (?, ?, ?)",
            [(1, "user_a", "小林"), (2, "user_b", "小周"), (3, "user_c", "小陈")],
        )
        conn.executemany(TASK_INSERT, [
            (1, 1, "整理需求", "todo", BASE_TIME, None),
            (2, 1, "写 SQL 练习", "todo", BASE_TIME, None),
            (3, 2, "修复加载提示", "done", BASE_TIME + 2, BASE_TIME + 5),
        ])
        conn.execute(
            "INSERT INTO task_events (task_id, kind, created_at) VALUES (?, ?, ?)",
            (3, "completed", BASE_TIME + 5),
        )
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def constraint_checks(conn):
    bad_tasks = [
        ("foreign key", (90, 999, "无主任务", "todo", BASE_TIME, None)),
        ("not null", (91, None, "无主任务", "todo", BASE_TIME, None)),
        ("empty title", (92, 1, "   ", "todo", BASE_TIME, None)),
        ("invalid status", (93, 1, "错误状态", "paused", BASE_TIME, None)),
        ("missing completion time", (94, 1, "错误时间", "done", BASE_TIME, None)),
        ("strict integer", (95, 1, "错误类型", "todo", "yesterday", None)),
    ]
    rejected = 0
    for label, values in bad_tasks:
        try:
            conn.execute(TASK_INSERT, values)
        except sqlite3.IntegrityError:
            rejected += 1
        else:
            raise AssertionError("Constraint did not reject: " + label)
    try:
        conn.execute(
            "INSERT INTO users (id, handle, display_name) VALUES (?, ?, ?)",
            (99, "user_a", "重复账号"),
        )
    except sqlite3.IntegrityError:
        rejected += 1
    else:
        raise AssertionError("UNIQUE did not reject the duplicate handle")
    assert conn.execute("SELECT count(*) FROM tasks").fetchone() == (3,)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    print("constraints: %d/7 invalid writes rejected" % rejected)


def query_checks(conn):
    rows = conn.execute(TASK_QUERY, (1,)).fetchall()
    assert [row[0] for row in rows] == [2, 1]
    assert conn.execute(
        "SELECT count(*) FROM tasks WHERE completed_at = NULL"
    ).fetchone() == (0,)
    assert conn.execute(
        "SELECT count(*) FROM tasks WHERE completed_at IS NULL"
    ).fetchone() == (2,)
    counts = conn.execute("""
        SELECT u.id, u.display_name, count(t.id) AS todo_count
        FROM users AS u
        LEFT JOIN tasks AS t ON t.owner_id = u.id AND t.status = 'todo'
        GROUP BY u.id, u.display_name
        ORDER BY u.id
    """).fetchall()
    assert counts == [(1, "小林", 2), (2, "小周", 0), (3, "小陈", 0)]
    payload = "x' OR 1=1 --"
    assert conn.execute(
        "SELECT id FROM users WHERE handle = ?", (payload,)
    ).fetchall() == []
    print("queries: ordered ids=%s; LEFT JOIN counts=%s" % (
        [row[0] for row in rows], [row[2] for row in counts],
    ))
    print("null and bound-parameter checks: passed")


def complete_task(conn, task_id, owner_id, completed_at, *, event_kind="completed"):
    """Own one transaction; event_kind is a demonstration fault-injection hook."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = conn.execute("""
            UPDATE tasks
            SET status = 'done', completed_at = ?
            WHERE id = ? AND owner_id = ? AND status = 'todo'
        """, (completed_at, task_id, owner_id)).rowcount
        if changed == 0:
            conn.execute("ROLLBACK")
            return False
        conn.execute(
            "INSERT INTO task_events (task_id, kind, created_at) VALUES (?, ?, ?)",
            (task_id, event_kind, completed_at),
        )
        conn.execute("COMMIT")
        return True
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def task_state(conn, task_id):
    return conn.execute(
        "SELECT status, completed_at FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()


def event_count(conn, task_id):
    return conn.execute(
        "SELECT count(*) FROM task_events WHERE task_id = ?", (task_id,)
    ).fetchone()[0]


def transaction_checks(conn):
    try:
        complete_task(conn, 1, 1, BASE_TIME + 10, event_kind="invalid")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("The invalid event was unexpectedly accepted")
    assert task_state(conn, 1) == ("todo", None)
    assert event_count(conn, 1) == 0
    assert not conn.in_transaction
    print("rollback: task 1=todo; completion events=0")
    assert complete_task(conn, 1, 1, BASE_TIME + 10) is True
    assert task_state(conn, 1) == ("done", BASE_TIME + 10)
    assert event_count(conn, 1) == 1
    assert complete_task(conn, 1, 1, BASE_TIME + 11) is False
    assert task_state(conn, 1) == ("done", BASE_TIME + 10)
    assert event_count(conn, 1) == 1
    print("commit and repeat: task 1=done; completion events=1")


def writer_checks(path):
    with closing(connect(path)) as writer, closing(connect(path)) as other:
        try:
            assert task_state(other, 2) == ("todo", None)
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("""
                UPDATE tasks SET status = 'done', completed_at = ? WHERE id = 2
            """, (BASE_TIME + 20,))
            writer.execute("""
                INSERT INTO task_events (task_id, kind, created_at)
                VALUES (2, 'completed', ?)
            """, (BASE_TIME + 20,))
            # The SELECT cursor is consumed; other holds no explicit read transaction.
            assert task_state(other, 2) == ("todo", None)
            try:
                other.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as error:
                # Python 3.11+ exposes the structured SQLite error code.
                code = getattr(error, "sqlite_errorcode", None)
                if code is not None:
                    assert (code & 0xff) == sqlite3.SQLITE_BUSY
                else:
                    assert "locked" in str(error).lower()
                assert not other.in_transaction
                print("second writer: busy (timeout=0)")
            else:
                raise AssertionError("Two write transactions were active together")
            writer.execute("COMMIT")
            assert task_state(other, 2) == ("done", BASE_TIME + 20)
            assert event_count(other, 2) == 1
            print("other connection reads: todo before commit; done after commit")
        finally:
            for conn in (writer, other):
                if conn.in_transaction:
                    conn.execute("ROLLBACK")


def seed_large(conn):
    tasks = []
    for number in range(20_000):
        task_id = number + 1
        owner_id = number % 100 + 1
        status = "todo" if (number // 100) % 4 == 0 else "done"
        created_at = BASE_TIME + number // 500
        completed_at = None if status == "todo" else created_at + 60
        tasks.append((task_id, owner_id, "任务 %d" % task_id,
                      status, created_at, completed_at))
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.executemany(
            "INSERT INTO users (id, handle, display_name) VALUES (?, ?, ?)",
            [(n, "user_%d" % n, "用户 %d" % n) for n in range(1, 101)],
        )
        conn.executemany(TASK_INSERT, tasks)
        conn.execute("""
            INSERT INTO task_events (task_id, kind, created_at)
            SELECT id, 'completed', completed_at FROM tasks WHERE status = 'done'
        """)
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    matching = [row for row in tasks if row[1] == 7 and row[3] == "todo"]
    assert len(matching) == 50
    expected = sorted(matching, key=lambda row: (row[4], row[0]), reverse=True)[:20]
    return [(row[0], row[2], row[4]) for row in expected]


def print_plan(conn, label, query=TASK_QUERY):
    print(label + ":")
    for row in conn.execute("EXPLAIN QUERY PLAN " + query, (7,)).fetchall():
        print("  " + row[3])


def index_checks(conn):
    expected = seed_large(conn)
    stages = [
        ("no query index", None),
        ("filter index", "CREATE INDEX idx_tasks_owner_status ON tasks(owner_id, status)"),
        ("filter and order index", """
            CREATE INDEX idx_tasks_owner_status_created
            ON tasks(owner_id, status, created_at DESC, id DESC)
        """),
    ]
    print("planner data: tasks=20000; owners=100; owner 7 todo=50; LIMIT=20")
    for label, ddl in stages:
        if label == "filter and order index":
            conn.execute("DROP INDEX idx_tasks_owner_status")
        if ddl:
            conn.execute(ddl)
        conn.execute("ANALYZE")
        print_plan(conn, label)
        assert conn.execute(TASK_QUERY, (7,)).fetchall() == expected
    narrow_query = TASK_QUERY.replace("id, title, created_at", "id, created_at")
    print_plan(conn, "projection without title", narrow_query)
    assert conn.execute(narrow_query, (7,)).fetchall() == [
        (row[0], row[2]) for row in expected
    ]
    print("all index stages: same 20 rows, matching the Python reference sort")


def main():
    if not __debug__:
        raise SystemExit("Run without -O so experiment assertions remain enabled")
    if sys.version_info < (3, 9) or sqlite3.sqlite_version_info < (3, 37, 0):
        raise SystemExit("Requires Python 3.9+ and SQLite 3.37+ (STRICT tables)")
    print("Python %s; SQLite %s; %s %s" % (
        platform.python_version(), sqlite3.sqlite_version,
        platform.system(), platform.machine(),
    ))
    with tempfile.TemporaryDirectory(prefix="sql-task-demo-") as directory:
        small_path = Path(directory) / "small.db"
        with closing(connect(small_path)) as conn:
            create_database(conn)
            seed_small(conn)
            constraint_checks(conn)
            query_checks(conn)
            transaction_checks(conn)
        writer_checks(small_path)
        with closing(connect(Path(directory) / "planner.db")) as conn:
            create_database(conn)
            index_checks(conn)
    print("PASS; temporary databases removed")


if __name__ == "__main__":
    main()
