"""Bounded local corpus search/fetch. URLs are provenance, never fetch targets."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import stat
from typing import Protocol
from urllib.parse import urlsplit

from agent_runtime import confined_path

MAX_DOCUMENT_BYTES = 24_000
MAX_CORPUS_DOCUMENTS = 20
MAX_MANIFEST_BYTES = 32_000


def strict_json(text: str):
    def reject_constant(value):
        raise ValueError("Non-finite JSON number")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_pairs)


def read_limited(path: Path, limit: int) -> bytes:
    """Only regular, non-symlink files; do not silently truncate evidence."""
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Corpus entries must be regular files")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Corpus file exceeds byte limit")
    return data


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    file: str
    text: str
    sha256: str
    retrieved_at: str
    url: str | None = None
    published_at: str | None = None
    publisher: str | None = None

    def provenance(self) -> dict:
        return {key: value for key, value in asdict(self).items() if key != "text"}


class SourceProvider(Protocol):
    """Search results discover IDs; only fetch returns citable source content."""

    def catalog(self) -> list[dict]: ...
    async def search(self, query: str, limit: int = 5) -> dict: ...
    async def fetch(self, source_id: str) -> Source: ...


class CorpusProvider:
    def __init__(self, manifest: Path, *, request_timeout: float = 5.0):
        if not math.isfinite(request_timeout) or request_timeout <= 0:
            raise ValueError("Source timeout must be positive")
        manifest = Path(manifest).absolute()
        self.root = manifest.parent
        manifest = confined_path(self.root, manifest.name)
        data = strict_json(read_limited(manifest, MAX_MANIFEST_BYTES).decode("utf-8"))
        if not isinstance(data, dict) or set(data) != {"label", "documents"}:
            raise ValueError("Corpus needs exactly label and documents")
        if not isinstance(data["label"], str) or not 1 <= len(data["label"]) <= 200:
            raise ValueError("Invalid corpus label")
        entries = data["documents"]
        if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_CORPUS_DOCUMENTS:
            raise ValueError("Corpus needs 1–20 documents")
        self.label = data["label"]
        self.entries: dict[str, dict] = {}
        for item in entries:
            required = {"id", "title", "file"}
            optional = {"url", "published_at", "publisher"}
            if (not isinstance(item, dict) or not required <= set(item)
                    or set(item) - required - optional):
                raise ValueError("Malformed corpus source metadata")
            if not isinstance(item["id"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", item["id"]):
                raise ValueError("Invalid source ID")
            if item["id"] in self.entries:
                raise ValueError("Duplicate source ID")
            for key in ("title", "file"):
                if not isinstance(item[key], str) or not 1 <= len(item[key]) <= 300:
                    raise ValueError("Invalid source " + key)
            confined_path(self.root, item["file"])
            if "url" in item:
                if not isinstance(item["url"], str) or len(item["url"]) > 1500:
                    raise ValueError("Invalid source URL")
                url = urlsplit(item["url"])
                if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
                    raise ValueError("Source URL must be an HTTP(S) bibliographic reference")
            if "published_at" in item:
                if not isinstance(item["published_at"], str):
                    raise ValueError("Invalid source publication date")
                date.fromisoformat(item["published_at"])
            if "publisher" in item and (not isinstance(item["publisher"], str)
                                          or not 1 <= len(item["publisher"]) <= 200):
                raise ValueError("Invalid publisher")
            self.entries[item["id"]] = dict(item)
        self.request_timeout = request_timeout

    def catalog(self) -> list[dict]:
        return [{"source_id": entry["id"], "title": entry["title"]}
                for entry in self.entries.values()]

    async def _read(self, entry: dict) -> tuple[bytes, str]:
        # Small regular local files only. Async cancellation bounds the wait, not
        # the lifetime of an OS/filesystem read already executing in a thread.
        path = confined_path(self.root, entry["file"])
        async with asyncio.timeout(self.request_timeout):
            raw = await asyncio.to_thread(read_limited, path, MAX_DOCUMENT_BYTES)
        text = raw.decode("utf-8")
        if not text.strip() or "\x00" in text:
            raise ValueError("Source must contain nonempty UTF-8 text without NUL")
        return raw, text

    async def search(self, query: str, limit: int = 5) -> dict:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 240:
            raise ValueError("Search query must contain 1–240 characters")
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("Search limit must be 1–5")
        terms = re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]", query.casefold())
        hits = []
        for entry in self.entries.values():
            _, text = await self._read(entry)
            haystack = (entry["id"] + " " + entry["title"] + " " + text).casefold()
            score = sum(haystack.count(term) for term in terms)
            if score:
                hits.append({"source_id": entry["id"], "title": entry["title"],
                             "snippet": text[:160], "score": score})
        hits.sort(key=lambda item: (-item["score"], item["source_id"]))
        return {"query": query, "hits": hits[:limit]}

    async def fetch(self, source_id: str) -> Source:
        # No URL, DNS, redirect, proxy or HTTP client exists in this provider.
        if source_id not in self.entries:
            raise ValueError("Unknown corpus source ID; URLs cannot be fetched")
        entry = self.entries[source_id]
        raw, text = await self._read(entry)
        return Source(source_id, entry["title"], entry["file"], text,
                      hashlib.sha256(raw).hexdigest(),
                      datetime.now(timezone.utc).isoformat(),
                      entry.get("url"), entry.get("published_at"), entry.get("publisher"))
