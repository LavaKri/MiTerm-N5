"""Smoke program of the early packaging test (``specs/packaging.md``).

Built by ``packaging/smoke.spec`` and driven by ``tools/check_packaging.py``. It does what the real
application will need from its folder, and writes the result in files, since a windowed program has
no console:
- loads wxPython and opens a window;
- runs a program under ConPTY and reads what it wrote through the screen model (pywinpty, pyte);
- checks the files pywinpty needs and that pyte stays separate files (LGPL);
- starts a new session of itself (``--child``), as "new session" will do;
- writes its diagnostic log to a file.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

import pyte
import winpty
import wx

from n5terminal import __version__
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.transport.conpty_transport import ConPtyLaunch, ConPtyTransport
from n5terminal.core.transport.transport import Stream, TransportState

logger = logging.getLogger("n5terminal.smoke")

WINPTY_FILES = ("conpty.dll", "OpenConsole.exe", "winpty.dll", "winpty-agent.exe")
MESSAGE = "packaged ok"
TIMEOUT = 30.0  # the words are separate arguments: one argument with a space would be quoted


class Collector:
    """A transport listener keeping the bytes and the exit code."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.exit_code: int | None = None
        self.closed = threading.Event()

    def on_state_changed(self, state: TransportState) -> None:
        logger.info("transport state: %s", state.value)
        if state in (TransportState.CLOSED, TransportState.FAILED):
            self.closed.set()

    def on_data(self, stream: Stream, data: bytes) -> None:
        self.data.extend(data)

    def on_exit(self, exit_code: int | None) -> None:
        self.exit_code = exit_code


def check_window() -> str:
    app = wx.App()
    frame = wx.Frame(None, title="MiTerm-N5 smoke")
    frame.Show()
    wx.CallLater(300, frame.Close)
    app.MainLoop()
    return str(wx.version())


def check_conpty(folder: Path) -> dict[str, object]:
    arguments = ("cmd.exe", "/c", "echo", *MESSAGE.split())
    transport = ConPtyTransport(ConPtyLaunch(arguments, folder))
    collector = Collector()
    transport.start(collector)
    closed = collector.closed.wait(TIMEOUT)
    transport.close()
    model = PyteScreenModel()
    model.feed(bytes(collector.data))
    lines = [row.text for row in model.take_update().rows if row.text]
    return {
        "closed": closed,
        "exit_code": collector.exit_code,
        "lines": lines,
        "ok": closed and collector.exit_code == 0 and MESSAGE in lines,
    }


def check_files() -> dict[str, object]:
    winpty_folder = Path(winpty.__file__).parent
    missing = [name for name in WINPTY_FILES if not (winpty_folder / name).exists()]
    pyte_file = Path(pyte.__file__)
    return {
        "winpty_folder": str(winpty_folder),
        "winpty_missing": missing,
        "pyte_file": str(pyte_file),
        "pyte_is_source": pyte_file.suffix == ".py" and pyte_file.exists(),
        "ok": not missing and pyte_file.suffix == ".py" and pyte_file.exists(),
    }


def new_session_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(Path(__file__).resolve())]


def start_new_session(out: Path) -> dict[str, object]:
    command = [*new_session_command(), "--child", "--out", str(out)]
    logger.info("starting a new session")
    completed = subprocess.run(
        command, creationflags=subprocess.CREATE_NO_WINDOW, timeout=TIMEOUT * 3, check=False
    )
    return {"return_code": completed.returncode, "ok": completed.returncode == 0}


def run(out: Path, role: str) -> dict[str, object]:
    report: dict[str, object] = {
        "role": role,
        "version": __version__,
        "pid": os.getpid(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "stdout_is_none": sys.stdout is None,
    }
    report["wx"] = check_window()
    report["files"] = check_files()
    report["conpty"] = check_conpty(out)
    if role == "parent":
        report["new_session"] = start_new_session(out)
    checks = [report[name] for name in ("files", "conpty", "new_session") if name in report]
    report["ok"] = all(isinstance(check, dict) and check["ok"] for check in checks)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    role = "child" if args.child else "parent"
    logging.basicConfig(
        filename=out / f"{role}.log",
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("smoke %s, MiTerm-N5 %s", role, __version__)
    try:
        report = run(out, role)
    except Exception:
        logger.exception("the smoke program failed")
        raise
    (out / f"{role}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("done, ok=%s", report["ok"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
