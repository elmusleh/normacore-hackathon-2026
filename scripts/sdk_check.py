#!/usr/bin/env python3
"""Read-only check that the NormaCore SDK and the Station binary match.

Both must come from release 0.1.0-beta.10 (build 5f4f805). A mismatch can cause
protocol or protobuf errors that look like hardware faults.

Exit 0 when every check passes (warnings do not fail). Exit 1 when a check fails.
Never moves the arm and never changes torque.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT / "external" / "norma-core"  # git submodule, pinned in .gitmodules
STATION = ROOT / "bin" / "station"

EXPECTED_VERSION = "0.1.0-beta.10"
EXPECTED_BUILD = "5f4f805"
EXPECTED_COMMIT = "5f4f8059deb0be9b8fa4de231a8754531bf3ffe1"
SDK_IMPORTS = ("software.station.shared.station_py", "target.gen_python")

statuses = []


def report(status, name, detail):
    statuses.append(status)
    print(f"[{status}] {name}: {detail}")


def git_in_sdk(*args):
    result = subprocess.run(["git", "-C", str(SDK), *args], capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout.strip()


def check_sdk():
    if not SDK.is_dir() or not any(SDK.iterdir()):
        report("FAIL", "SDK submodule", "empty or missing; run: git submodule update --init external/norma-core")
        return
    report("PASS", "SDK folder", str(SDK.relative_to(ROOT)))

    code, head = git_in_sdk("rev-parse", "HEAD")
    if code == 0 and head == EXPECTED_COMMIT:
        report("PASS", "SDK pin", f"commit {EXPECTED_COMMIT[:7]}")
    else:
        report("FAIL", "SDK pin", f"checked out {head[:7] or 'unknown'}, expected {EXPECTED_BUILD}; run: git submodule update --init")

    code, dirty = git_in_sdk("status", "--porcelain")
    if code == 0 and not dirty:
        report("PASS", "SDK local changes", "none")
    else:
        report("FAIL", "SDK local changes", "files in external/norma-core were edited or regenerated; reset them, do not commit them")

    cargo = SDK / "Cargo.toml"
    match = re.search(r'^version\s*=\s*"([^"]+)"', cargo.read_text(), re.M) if cargo.exists() else None
    found = match.group(1) if match else "none"
    if found == EXPECTED_VERSION:
        report("PASS", "SDK version", found)
    else:
        report("FAIL", "SDK version", f"found {found}, expected {EXPECTED_VERSION}")

    sys.path.insert(0, str(SDK))
    for module in SDK_IMPORTS:
        try:
            __import__(module)
            report("PASS", f"import {module}", "ok")
        except Exception as exc:  # any import error is a failed check
            report("FAIL", f"import {module}", f"{type(exc).__name__}: {exc}")


def check_station():
    if not STATION.exists():
        report("FAIL", "Station binary", "missing bin/station (see docs/team_setup.md step 4)")
        return
    try:
        result = subprocess.run([str(STATION), "--version"], capture_output=True, text=True, timeout=20)
        output = (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        output = f"{type(exc).__name__}: {exc}"
    match = re.search(r"station (\S+) \((\w+)\)", output)
    if match and match.group(1) == EXPECTED_VERSION and match.group(2) == EXPECTED_BUILD:
        report("PASS", "Station build", output)
    else:
        report("FAIL", "Station build", f"got '{output or 'no output'}', expected {EXPECTED_VERSION} ({EXPECTED_BUILD})")


def main():
    check_sdk()
    check_station()
    failed = statuses.count("FAIL")
    print("RESULT: PASS" if failed == 0 else f"RESULT: {failed} check(s) FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
