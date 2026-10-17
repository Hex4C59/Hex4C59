# Persistent-memory agent

Python 3.11+. The default demonstration uses **fixture / 本地固定响应**. It executes real SQLite transactions and tools, starts separate Python processes, and runs a separate `demo_application/main.py`. It does not contact a model service or overwrite the tutorial's `app.py`.

## Downloaded ZIP

The ZIP includes `app.py`, `test_app.py`, this README, `agent_runtime.py`, and the shared pinned `requirements.txt`.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python -m unittest -v
```

On PowerShell activate with `.venv\Scripts\Activate.ps1`. Run commands from the extracted directory. The offline fixture still needs `jsonschema` from the shared requirements; it needs neither credentials nor a live model.

## Repository checkout

From `examples/agents/persistent-memory`, use the Python environment prepared for these tutorials:

```sh
PYTHONPATH=../common python app.py
PYTHONPATH=../common python -m unittest -v
```

No extra dependencies are needed for SQLite; this example uses Python's `sqlite3` module.

## What the default demo actually checks

A fresh temporary directory contains both the database and an independent demo application. A first child process creates the application and saves two exact, pre-approved synthetic records for `demo-alice`. The parent then inserts a conflicting synthetic preference for `demo-bob`. A new child process constructs a new store and client for `demo-alice`, retrieves her preference and event, and verifies that Bob's value appears in none of the actual model requests. Finally the parent executes the generated application. The temporary directory is cleaned on exit.

Captured fixture stdout, 2026-10-17:

```text
fixture / 本地固定响应；真实 SQLite、独立子进程和临时演示应用
fixture seed: user=demo-alice session=session-1; saved=2
fixture request budget: max=3986/16000 characters
fixture restart: user=demo-alice session=session-2; response_style=简洁，先给结论
fixture isolation: other user's preference absent from every model request
fixture request budget: max=3098/16000 characters
demo_application/main.py: {"status": "ok"}
fixture: temporary workspace removed; tutorial app.py was not modified
```

These are fixture outputs and local integration evidence, not evidence of model quality. Request character counts may change with the shared tool descriptions or source edits.

## Explicit user, session and data selection

Every command other than the temporary demo requires `--workspace`, `--user`, and `--session`. The database defaults to `<workspace>/state/memory.sqlite3`; `--data-dir` explicitly chooses another directory. There is no default user and no data directory under HOME or the checkout. `session` records where a memory was last confirmed; another session for the same user can retrieve it.

The following macOS/Linux commands use only a new temporary workspace and synthetic values. Each Python invocation is a fresh process. PowerShell users should set `$memory_demo` to a newly created practice directory instead of using `mktemp`.

```sh
memory_demo=$(mktemp -d)
python app.py put --workspace "$memory_demo" --user sample-a --session one --key response_style --value 'synthetic concise' --confirm
python app.py get --workspace "$memory_demo" --user sample-a --session two --key response_style
python app.py search --workspace "$memory_demo" --user sample-a --session two --query concise --limit 5
python app.py put --workspace "$memory_demo" --user sample-a --session two --key response_style --value 'synthetic short paragraphs' --confirm
python app.py delete --workspace "$memory_demo" --user sample-a --session two --key response_style --confirm
python app.py get --workspace "$memory_demo" --user sample-a --session three --key response_style
```

The update increments `revision`; the final get returns `{"record":null}`. Omitting `--confirm` makes put/delete fail without mutation. Choose an explicit directory you own if you want records to outlive this exercise; clean only the temporary directory you created.

## Agent tools and confirmation

`memory_get`, `memory_search`, `memory_put`, `memory_delete`, and `write_demo_file` run through the shared validated loop. Every schema rejects extra properties. Tools do **not** accept a user ID: the application binds the selected user outside the model. Supplying a different `user_id` is a schema error.

A model cannot approve its own write. For a chat invocation, `--confirm-preference KEY VALUE` permits that exact preference once; `--confirm-delete KIND KEY` permits that exact deletion once. A different value, an unconfirmed key, or a second write using a consumed confirmation is rejected. A commit failure leaves the confirmation available to retry. No model extraction runs on exit, and merely mentioning a preference does not save it.

```sh
python app.py chat --workspace "$memory_demo" --user sample-a --session four --confirm-preference response_style 'synthetic concise' --task '保存我在命令行确认的值，然后查询记忆。'
```

Without `--live`, that command uses fixed tool calls and labels its final response `fixture`. Inspect the real stored result with `get` or `search`. Direct `put --kind episode --confirm` can also save a confirmed event; the two kinds are independent keys.

Live mode uses the shared **async** adapter. Set `OPENAI_API_KEY` and `OPENAI_MODEL` in your terminal; optionally select `OPENAI_BASE_URL`. No particular model is hard-coded. The adapter is always closed in `finally`, including a model error or cancellation.

```sh
python app.py chat --live --workspace "$memory_demo" --user sample-a --session five --task '查询已经确认的回答偏好；不要保存新资料。'
```

No live-model call was made for this implementation pass because credentials were absent. Missing credentials fail explicitly; there is no fixture fallback for `--live`.

## Bounds and deletion semantics

- Each memory value: at most 512 Unicode characters; each user: at most 64 records; whole store: at most 1024 records. Creation quotas and the upsert are checked inside the same `BEGIN IMMEDIATE` transaction. An existing key can still be updated at quota.
- Each application connection sets a 16 MiB SQLite page limit. This does not bound rollback-journal overhead or other programs bypassing the application.
- Retrieval contains whole records and at most 2200 characters of canonical JSON. Up to five confirmed preferences are selected first; event retrieval uses bounded substring queries over words in the task. Search folds ASCII case and otherwise matches literal text, including Chinese. It is not embedding or semantic search.
- Session history stays in RAM, at most eight user/assistant pairs and 4000 canonical-JSON characters. Long historical text is explicitly truncated; oldest whole pairs are removed. It is not a persistent transcript.
- **Before every model call**, `BudgetedModel` compacts history, retrieved records, then older complete assistant/tool exchanges. It counts the canonical JSON of both `messages` and `tools`, and refuses a request over 16000 Unicode characters. It never splits a tool-call/result group. If the current task, schemas or newest exchange cannot fit, the underlying model is not called. This is a measured character budget, not a tokenizer or a claim about provider token limits, HTTP serialization, or output size.
- A confirmed tool deletion clears the local history and skips retaining that turn. There is no exit-time extraction to recreate the deleted record. A model may already have seen a retrieved value earlier in the current request; deletion cannot retract that input. SQLite deletion is logical deletion, not secure erasure of all disk remnants.

User IDs provide application-level selection, not authentication or isolation from another local process that can open the database. Workspace path checks reject traversal and symlink paths for the demo tools; they are not an OS sandbox. This example has no arbitrary shell tool. Real deployment needs an authenticated source for user identity and a data lifecycle appropriate to its users.

## Failure and verification scope

A corrupt, unsupported or malformed database is rejected without resetting existing contents. Locked/failed writes return errors and roll back; tool failures are structured `ok:false` results, which a model can inspect. They are not successful saves merely because an assistant finishes a response.

`python -m unittest -v` currently runs 19 tests, covering real process restart, user isolation, updates/deletes, literal search, quotas and rollback, concurrent writers, corrupt/malformed/locked stores, explicit CLI scope/confirmation, invalid model arguments, traversal, exact and one-use approvals, history limits, whole-exchange compaction, pre-call refusal, cancellation, and async client closure. All test records are synthetic and all databases/applications are in temporary directories. Network quality, model compliance, disk-power failure, authenticated multi-tenant hosting and secure deletion are outside this evidence.
