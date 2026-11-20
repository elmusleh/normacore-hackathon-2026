"""Run logging for the ElRobot tools.

Every run writes a full DEBUG log to `logs/<name>-<timestamp>.log` and updates
`logs/<name>-latest.log` to point at it, so `./cli.sh logs` always shows the
last run. The console shows INFO and above (DEBUG with --debug).

Each log starts with a run header (git commit, Python, platform, arguments,
SDK path) so a log file alone is enough to reproduce the setup. Uncaught
exceptions are written with full tracebacks.
"""

from __future__ import annotations

import atexit
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.environ.get("ELROBOT_LOG_DIR", ROOT / "logs"))

FILE_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s:%(lineno)d | %(message)s"
CONSOLE_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
DATE_FORMAT = "%H:%M:%S"

_started_monotonic = time.monotonic()


def _git_hash() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - header must never fail the run
        return "unknown"


def _point_latest(name: str, target: Path) -> None:
    """Make logs/<name>-latest.log point at the newest run. Falls back to a copy on Windows."""
    link = LOG_DIR / f"{name}-latest.log"
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target.name)
    except OSError:
        try:
            link.write_text(target.read_text())
        except OSError:
            pass


def setup_logging(
    name: str,
    debug: bool = False,
    argv: list | None = None,
    console_level: int | None = None,
) -> Path:
    """Configure root logging for one tool run. Returns the log file path.

    console_level overrides the console threshold (default INFO, DEBUG with debug=True).
    The file always gets DEBUG.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = LOG_DIR / f"{name}-{stamp}.log"

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    if console_level is None:
        console_level = logging.DEBUG if debug else logging.INFO
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT))
    root.addHandler(console)

    _point_latest(name, path)

    log = logging.getLogger("elrobot.run")
    log.debug("log file: %s", path)
    log.debug("header: tool=%s git=%s python=%s platform=%s cwd=%s argv=%s sdk_root=%s",
              name, _git_hash(), platform.python_version(), platform.platform(),
              os.getcwd(), argv if argv is not None else sys.argv,
              os.environ.get("NORMACORE_ROOT", "external/norma-core (default)"))

    def _excepthook(exc_type, exc, tb):
        logging.getLogger("elrobot.crash").critical(
            "uncaught exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

    @atexit.register
    def _footer():
        logging.getLogger("elrobot.run").debug(
            "run finished after %.2fs", time.monotonic() - _started_monotonic)

    return path
