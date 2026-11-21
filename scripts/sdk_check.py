#!/usr/bin/env python3
"""Read-only check that the NormaCore SDK and the Station binary match.

Both must come from release 0.1.0-beta.10 (build 5f4f805). A mismatch can cause
protocol or protobuf errors that look like hardware faults.

Exit 0 when every check passes (warnings do not fail). Exit 1 when a check fails.
Never moves the arm and never changes torque.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT / "external" / "norma-core"
STATION = ROOT / "bin" / "station"
ARCHIVE = ROOT / "external" / "norma-core-main.tar.gz"

EXPECTED_VERSION = "0.1.0-beta.10"
EXPECTED_BUILD = "5f4f805"
EXPECTED_ARCHIVE_SHA256 = "0fb314f9ca41158bc42b9836467b162f0d5256e4118e56bfe6072eb93f17d829"
SDK_IMPORTS = ("software.station.shared.station_py", "target.gen_python")

statuses = []


def report(status, name, detail):
    statuses.append(status)
    print(f"[{status}] {name}: {detail}")


def check_sdk():
    if not SDK.is_dir():
        report("FAIL", "SDK folder", f"missing {SDK.relative_to(ROOT)} (see docs/team_setup.md step 4)")
        return
    report("PASS", "SDK folder", str(SDK.relative_to(ROOT)))

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


def check_archive():
    if not ARCHIVE.exists():
        report("WARN", "SDK archive", "not present (only needed to re-extract the SDK)")
        return
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest == EXPECTED_ARCHIVE_SHA256:
        report("PASS", "SDK archive sha256", digest[:16] + "...")
    else:
        report("FAIL", "SDK archive sha256", f"{digest} does not match the team's archive")


def main():
    check_sdk()
    check_station()
    check_archive()
    failed = statuses.count("FAIL")
    print("RESULT: PASS" if failed == 0 else f"RESULT: {failed} check(s) FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
