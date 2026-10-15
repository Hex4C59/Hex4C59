PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
) STRICT;

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at INTEGER NOT NULL,
    completed_at INTEGER,
    CHECK (
        (status = 'todo' AND completed_at IS NULL)
        OR (status = 'done' AND completed_at IS NOT NULL)
    )
) STRICT;

CREATE TABLE task_events (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind = 'completed'),
    created_at INTEGER NOT NULL
) STRICT;
