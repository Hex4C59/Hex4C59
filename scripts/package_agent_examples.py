#!/usr/bin/env python3
"""Build deterministic, self-contained ZIPs for the Agent tutorials."""
import argparse
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "examples/agents"
IGNORED = {"__pycache__", ".venv", ".pytest_cache", ".git", ".DS_Store"}
SUFFIXES = {".py", ".md", ".txt", ".json", ".html", ".yaml", ".yml", ".toml", ".diff"}
PINNED = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+!-]+")


def manifest(source=SOURCE):
    data = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if not data or any(not re.fullmatch(r"[a-z][a-z0-9-]*", name) for name in data):
        raise ValueError("Invalid example manifest")
    return data


def requirements(source, name):
    lines = []
    seen = {}
    paths = [source / "common/requirements.txt", source / name / "requirements-extra.txt"]
    for path in paths:
        if not path.exists():
            if path.name == "requirements-extra.txt":
                continue
            raise ValueError("Missing shared requirements")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if not PINNED.fullmatch(line):
                raise ValueError("Only exact dependency pins are allowed: " + str(path))
            package = line.split("==")[0].lower().replace("_", "-")
            if package in seen and seen[package] != line:
                raise ValueError("Conflicting dependency pins: " + package)
            if package not in seen:
                seen[package] = line
                lines.append(line)
    return ("\n".join(lines) + "\n").encode()


def archive_files(source, name):
    if name not in manifest(source):
        raise ValueError("Unknown example: " + name)
    directory = source / name
    if directory.is_symlink():
        raise ValueError("Example directory cannot be a symlink")
    files = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("Example packages cannot contain symlinks: " + str(relative))
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in relative.parts) or path.suffix not in SUFFIXES:
            raise ValueError("Unexpected example artifact: " + str(relative))
        if relative.as_posix() == "requirements.txt":
            raise ValueError("Use requirements-extra.txt; requirements.txt is generated")
        files[relative.as_posix()] = path.read_bytes()
    for required in ["app.py", "README.md", "test_app.py"]:
        if required not in files:
            raise ValueError("Missing example entry point: " + name + "/" + required)
    for filename, target in [("agent_runtime.py", "agent_runtime.py"),
                              ("README.md", "RUNTIME.md")]:
        key = target
        if key in files:
            raise ValueError("Example shadows shared runtime: " + key)
        files[key] = (source / "common" / filename).read_bytes()
    files["requirements.txt"] = requirements(source, name)
    return files


def check_archive(source, name, archive):
    expected = archive_files(source, name)
    with zipfile.ZipFile(archive) as packed:
        entries = [entry for entry in packed.infolist() if not entry.is_dir()]
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Archive entries differ from source: " + name)
        if any(packed.read(key) != data for key, data in expected.items()):
            raise ValueError("Archive contents differ from source: " + name)
    return len(expected)


def write_archives(destination, source=SOURCE):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in manifest(source):
        archive = destination / (name + ".zip")
        temporary = archive.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
                for key, data in sorted(archive_files(source, name).items()):
                    info = zipfile.ZipInfo(key, date_time=(2000, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    packed.writestr(info, data, compresslevel=9)
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
        results[name] = check_archive(source, name, archive)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            results = {name: check_archive(SOURCE, name, args.destination / (name + ".zip"))
                       for name in manifest()}
        else:
            results = write_archives(args.destination)
        for name, count in results.items():
            print("%s.zip: %d source files match" % (name, count))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
