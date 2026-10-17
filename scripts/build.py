#!/usr/bin/env python3
"""Build the blog with the pinned Hugo version and run publication checks."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from check_site import check_site
from package_course import ARCHIVE, COURSE, check_archive
from package_agent_examples import write_archives

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "public")
    parser.add_argument("--base-url")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    expected = (ROOT / ".hugo-version").read_text().strip()
    try:
        version = subprocess.check_output(["hugo", "version"], text=True)
        match = re.search(r"hugo v([\d.]+)", version)
        if not match or match.group(1) != expected:
            raise ValueError("Expected Hugo %s; found %s" % (expected, version.strip()))
        count = check_archive(COURSE, ARCHIVE)
        print("Rust archive: %d matching source files" % count, flush=True)
        command = ["hugo", "--gc", "--minify", "--cleanDestinationDir", "--destination", str(args.destination.resolve())]
        if args.base_url:
            command.extend(["--baseURL", args.base_url])
        if args.cache_dir:
            command.extend(["--cacheDir", str(args.cache_dir.resolve())])
        subprocess.run(command, cwd=ROOT, check=True)
        packages = write_archives(args.destination / "downloads/agent-examples")
        print("Agent example archives: %d self-contained packages" % len(packages), flush=True)
        print(check_site(args.destination, args.base_url))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
