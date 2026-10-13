#!/usr/bin/env python3
"""Pack the Rust examples deterministically, or check archive/source consistency."""
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
COURSE = ROOT / "content/tutorials/rust-from-zero/course"
ARCHIVE = COURSE.parent / "course.zip"
PREFIX = "rust-course/"


def source_files(source):
    files = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in {"target", ".git", "__pycache__", ".DS_Store"} for part in relative.parts):
            continue
        if relative.as_posix() in {"tasks.tsv", "notes.txt"}:
            continue
        if path.is_symlink():
            raise ValueError("Course packages cannot contain symlinks: " + str(relative))
        if path.is_file():
            files[PREFIX + relative.as_posix()] = path.read_bytes()
    if not files:
        raise ValueError("Course source is empty: " + str(source))
    return files


def check_archive(source, archive):
    expected = source_files(source)
    with zipfile.ZipFile(archive) as packed:
        entries = [info for info in packed.infolist() if not info.is_dir()]
        names = [info.filename for info in entries]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate paths in course.zip")
        missing = sorted(set(expected) - set(names))
        extra = sorted(set(names) - set(expected))
        if missing or extra:
            raise ValueError("Archive paths differ; missing: %s; extra: %s" % (missing, extra))
        changed = [name for name, data in expected.items() if packed.read(name) != data]
        if changed:
            raise ValueError("Archive contents differ: " + ", ".join(changed))
    return len(expected)


def write_archive(source, archive):
    files = source_files(source)
    temporary = archive.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for name, data in files.items():
                info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                packed.writestr(info, data, compresslevel=9)
        temporary.replace(archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    return check_archive(source, archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        count = write_archive(COURSE, ARCHIVE) if args.write else check_archive(COURSE, ARCHIVE)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        return 1
    print("Rust archive matches %d source files%s" % (count, " (repacked)" if args.write else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
