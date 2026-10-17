# CLI Coding Agent

Python 3.11+. The default run is labelled **fixture / 本地固定响应**. It creates a temporary practice project, runs a real failing `unittest` command, reads and replaces the faulty file, then runs the real test again. Model decisions are fixed responses; this verifies the loop and tools, not model quality.

The download contains `app.py`, `test_app.py`, `agent_runtime.py` and pinned `requirements.txt`. In an extracted ZIP:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py --trace repair.jsonl
python app.py --summarize-trace repair.jsonl
python -m unittest -v
```

Inside the source repository, install `../common/requirements.txt`, then run with `PYTHONPATH=../common`. The shared runtime is maintained in `../common/agent_runtime.py`; the packager copies it into the ZIP. Trace destinations are new files: an existing file is never silently overwritten.

Captured stdout from an offline run (Python 3.11.16, 2026-10-17; selected lines):

```text
MODE fixture / 本地固定响应; exact demo commands and calculator.py write are preapproved.
RUNTIME status=complete turns=6 tool_calls=5
COMMAND 1: exit=1 timed_out=false truncated=false
COMMAND 2: exit=0 timed_out=false truncated=false
WRITES 1
```

The first failure is expected: `add(2, 3)` initially subtracts. The second process really executes the edited file and test. `complete` means the model loop ended; inspect command results separately. A final nonzero command or a run limit/error gives a nonzero application exit. No command at all means no test-execution evidence.

## Files, commands and approval

File tools reject absolute paths, parent traversal and symlink components. Reads/writes are capped at 16,384 bytes; existing files must be read before replacement, and parent directories must already exist. Listing visits at most 200 entries. These checks assume a trusted local workspace without another process racing to change it.

Every write and command goes through an approval callback. Write approval includes a real diff; if the file changes while awaiting approval, the write is rejected instead of overwriting that edit. The offline fixture explicitly preapproves only its exact demo commands and `calculator.py` write. Live mode shows the operation and asks for this one approval. Noninteractive stdin is denied. Async terminal approval needs an event loop supporting terminal readers; unsupported environments deny rather than block indefinitely.

Commands use an argument array and no shell. Their working directory is checked, but an approved program still has the current user's OS permissions and inherited environment. **This is not an OS sandbox**: a Python interpreter or another approved program can access paths beyond the file-tool root. Use only a disposable workspace and inspect the actual arguments before approving.

Both stdout and stderr are drained, with at most 4,096 bytes retained from each. Results include actual return code, total byte counts, truncation and timeout. A separate command deadline is 5 seconds by default (maximum 30); the whole model loop is bounded to 8 turns, 16 tools and 30 seconds. Timeout and cancellation kill and reap the direct child; POSIX cleanup also kills its new process group. Windows does not guarantee detached-descendant cleanup.

## Timeout and traces

```sh
python app.py --scenario timeout --command-timeout 0.1 --trace timeout.jsonl
python app.py --summarize-trace timeout.jsonl
```

The first command exits 1 by design: a real Python child prints `started`, sleeps, and is stopped. A return code such as `-9` depends on the OS; test the `timed_out` field instead of hard-coding that number.

JSONL has one JSON object per line. Default records include model/tool events from the shared runtime plus `approval.decision`, `file.read`, `file.write`, `process.start` and `process.end`. They omit prompts, file content, command arguments and stdout/stderr. `tool.end.ok=true` means dispatch and serialization succeeded; a returned command can still have `returncode=1`. The summary counts these separately and does not estimate tokens or price.

## Optional live use

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in your environment; `OPENAI_BASE_URL` is optional. Do not put credentials in files or shell history. Then select an existing disposable project:

```sh
python app.py --live --workspace /path/to/practice-project --task 'Fix the failing add test and run it' --trace live.jsonl
```

The shared adapter uses `AsyncOpenAI`; the client is closed in `finally`. There are no bundled credentials, no automatic fixture fallback, no chat-history resume and no streaming UI. Live network/API behavior was not verified in the offline test run.
