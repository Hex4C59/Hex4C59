#!/usr/bin/env python3
"""Test the exact downloadable Agent examples, with no model credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import zipfile

from package_agent_examples import SOURCE, manifest, write_archives, check_archive


def run(command, cwd, env, timeout):
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                                timeout=timeout, input="", check=False)
        return {"command": command, "returncode": result.returncode,
                "seconds": round(time.monotonic() - started, 3),
                "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"command": command, "returncode": 124,
                "seconds": round(time.monotonic() - started, 3),
                "stdout": "", "stderr": "Verification subprocess exceeded deadline"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--example", action="append", choices=tuple(manifest()),
                        help="Verify selected examples; repeat for multiple selections")
    parser.add_argument("--fresh-env", action="store_true",
                        help="Install each ZIP requirements into its own clean virtual environment")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    records = []
    try:
        with tempfile.TemporaryDirectory(prefix="agent-examples-check-") as temporary:
            root = Path(temporary)
            archives = args.archive_dir or root / "archives"
            if not args.archive_dir:
                write_archives(archives)
            env = os.environ.copy()
            # Fixture verification must not accidentally call a paid service.
            for name in list(env):
                if any(word in name.upper() for word in ("API_KEY", "AUTH_TOKEN", "OPENAI_BASE_URL", "OPENAI_MODEL")):
                    env.pop(name)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(SOURCE / "common")
            common = run([args.python, "-m", "unittest", "discover", "-v"], SOURCE / "common", env, args.timeout)
            records.append({"example": "common", "tests": common})
            if common["returncode"]:
                raise ValueError("Shared runtime verification failed")
            print("common: runtime tests passed", flush=True)
            for name in (args.example or manifest()):
                archive = archives / (name + ".zip")
                check_archive(SOURCE, name, archive)
                unpacked = root / "unpacked" / name
                unpacked.mkdir(parents=True)
                with zipfile.ZipFile(archive) as packed:
                    # check_archive has already verified the exact source entry set.
                    packed.extractall(unpacked)
                directory = unpacked
                env.pop("PYTHONPATH", None)
                interpreter = args.python
                installation = None
                if args.fresh_env:
                    venv = root / "environments" / name
                    created = run([args.python, "-m", "venv", str(venv)], directory, env, 120)
                    if created["returncode"]:
                        records.append({"example": name, "installation": created})
                        raise ValueError("Could not create isolated environment: " + name)
                    interpreter = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
                    installation = run([interpreter, "-m", "pip", "install", "-r", "requirements.txt"],
                                       directory, env, 240)
                    if installation["returncode"]:
                        records.append({"example": name, "installation": installation})
                        raise ValueError("ZIP dependencies could not be installed: " + name)
                tests = run([interpreter, "-m", "unittest", "discover", "-v", "-p", "test_*.py"],
                            directory, env, args.timeout)
                demo = run([interpreter, "app.py"], directory, env, args.timeout)
                matched = re.search(r"Ran (\d+) tests?", tests["stderr"])
                record = {"example": name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                          "tests": tests, "demo": demo, "installation": installation,
                          "test_count": int(matched.group(1)) if matched else 0}
                records.append(record)
                if tests["returncode"] or demo["returncode"] or not record["test_count"]:
                    raise ValueError("Example verification failed: " + name)
                if "fixture" not in (demo["stdout"] + demo["stderr"]).lower():
                    raise ValueError("Offline demo must identify fixture mode: " + name)
                print("%s: %d tests and extracted-ZIP demo passed" % (name, record["test_count"]), flush=True)
        returncode = 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        for record in records[-1:]:
            for key in ("tests", "demo", "installation"):
                if record.get(key):
                    print(record[key].get("stdout", "")[-5000:], file=sys.stderr)
                    print(record[key].get("stderr", "")[-5000:], file=sys.stderr)
        returncode = 1
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"returncode": returncode, "results": records}, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return returncode


if __name__ == "__main__":
    sys.exit(main())
