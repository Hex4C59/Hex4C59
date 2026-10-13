#!/usr/bin/env python3
"""Check local URLs, assets, fragments and search entries in a Hugo build."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.urls = []
        self.canonical = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in (("id", "name") if tag == "a" else ("id",)):
            if attrs.get(key):
                self.ids.add(attrs[key])
        for key in ("href", "src", "poster", "data-index"):
            if attrs.get(key):
                self.urls.append(attrs[key])
        srcset = attrs.get("srcset", "")
        if srcset and "data:" not in srcset:
            self.urls.extend(item.strip().split()[0] for item in srcset.split(",") if item.strip())
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")


def check_site(destination, site_url=None):
    destination = destination.resolve()
    documents = {path: Document(path.read_text(encoding="utf-8")) for path in destination.rglob("*.html")}
    home = documents.get(destination / "index.html")
    if home is None:
        raise ValueError("Missing home page; build Hugo before running this check")
    base = urlsplit(site_url or home.canonical or "http://localhost/")
    prefix = base.path.rstrip("/") + "/"
    origin = "%s://%s" % (base.scheme, base.netloc)
    errors = []
    count = 0

    def check_url(source_url, href):
        nonlocal count
        target = urlsplit(urljoin(source_url, href))
        if target.scheme not in {"http", "https"} or target.netloc != base.netloc:
            return
        count += 1
        decoded = unquote(target.path)
        if not decoded.startswith(prefix):
            errors.append("%s: %s leaves site base path %s" % (source_url, href, prefix))
            return
        relative = decoded[len(prefix):]
        path = destination / relative
        if decoded.endswith("/"):
            path = path / "index.html"
        path = path.resolve()
        if destination not in path.parents or not path.is_file():
            errors.append("%s: missing local target %s" % (source_url, href))
            return
        if target.fragment and path.suffix == ".html":
            fragment = unquote(target.fragment)
            if fragment not in documents[path].ids:
                errors.append("%s: missing fragment %s" % (source_url, href))

    for path, document in documents.items():
        relative = path.relative_to(destination).as_posix()
        if path.name == "index.html":
            relative = relative[:-len("index.html")]
        source = origin + prefix + relative
        for href in document.urls:
            check_url(source, href)
    for path in destination.rglob("*.css"):
        source = origin + prefix + path.relative_to(destination).as_posix()
        for href in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)['\"]?\s*\)", path.read_text(encoding="utf-8")):
            check_url(source, href)
    index_path = destination / "index.json"
    if not index_path.is_file():
        errors.append("Missing search index: index.json")
        entries = []
    else:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        seen = set()
        for entry in entries:
            permalink = entry["permalink"]
            if permalink in seen:
                errors.append("Duplicate search entry: " + permalink)
            seen.add(permalink)
            check_url(origin + prefix, permalink)
    if errors:
        raise ValueError("\n".join(errors))
    return {"html_pages": len(documents), "local_urls_and_fragments": count, "search_entries": len(entries)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, nargs="?", default=Path("public"))
    parser.add_argument("--site-url")
    args = parser.parse_args()
    try:
        print(json.dumps(check_site(args.destination, args.site_url), ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
