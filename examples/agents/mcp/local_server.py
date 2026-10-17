"""A real, local FastMCP stdio server. Stdout is reserved for MCP messages."""
from __future__ import annotations

import argparse
import asyncio
import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def workspace_file(root: Path, relative: str) -> Path:
    # This check assumes a private, user-controlled directory without a process
    # racing to replace path components. It is not an OS sandbox.
    if not isinstance(relative, str) or not relative or "\0" in relative or "\\" in relative:
        raise ValueError("Use a nonempty relative path with / separators")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Absolute paths and parent traversal are forbidden")
    cursor = root
    for component in candidate.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError("Symlinks are forbidden")
    if not cursor.is_file():
        raise ValueError("Note is not a regular file")
    if cursor.stat().st_size > 8192:
        raise ValueError("Note exceeds 8192 bytes; use a smaller note")
    return cursor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--label", default="local")
    parser.add_argument("--probe-dir", type=Path, help="Test-only, explicit temporary PID marker directory")
    args = parser.parse_args()
    if args.workspace.is_symlink() or not args.workspace.is_dir():
        parser.error("workspace must be an existing non-symlink directory")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,15}", args.label):
        parser.error("invalid label")
    root = args.workspace.resolve()
    if args.probe_dir:
        # The tests supply a separate TemporaryDirectory; no HOME/checkout files.
        if not args.probe_dir.is_dir():
            parser.error("probe-dir must already exist")
        (args.probe_dir / f"{args.label}.pid").write_text(str(os.getpid()), encoding="utf-8")
    server = FastMCP(f"synthetic-notes-{args.label}", log_level="ERROR")

    @server.tool()
    async def read_note(path: str, delay_seconds: float = 0.0) -> dict[str, str]:
        """Read at most 8192 bytes from a relative UTF-8 note in the configured workspace.

        delay_seconds (0..5) exists for the cancellation/timeout exercise.
        """
        if not 0 <= delay_seconds <= 5:
            raise ValueError("delay_seconds must be between 0 and 5")
        target = workspace_file(root, path)
        await asyncio.sleep(delay_seconds)
        return {"label": args.label, "path": path, "text": target.read_text(encoding="utf-8")}

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
