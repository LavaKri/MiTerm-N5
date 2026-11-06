"""Experiment: can the prompt of a shell be told apart? (``specs/architecture/session.md``)

Usage: ``.venv\\Scripts\\python.exe tools\\probe_shell_prompt.py [cmd|powershell]``. Starts the
shell under ConPTY inside a Job object, types situations into it, and prints for each one how many
processes the job holds (the shell alone is 1) and the line the cursor is on. The result that made
the rule of ``core/session/shell_prompt.py``: one process is not enough (built-in commands that wait
have one too), the cursor line is not enough either, so both must agree.
"""

import shutil
import sys
import time
from pathlib import Path

import winpty

from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.transport.process_tree import ProcessTree

COLUMNS, ROWS = 120, 30
SETTLE = 1.5  # seconds given to a situation to show itself

SITUATIONS = {
    "cmd": [
        ("at the prompt", ""),
        ("dir (ends at once)", "dir /b\r"),
        ("ping, running", "ping -n 4 127.0.0.1 >nul\r"),
        ("(wait for the end of ping)", ""),
        ("(wait for the end of ping)", ""),
        ("at the prompt after ping", ""),
        ("python input(), waiting", 'python -c "input()"\r'),
        ("(Enter, the program ends)", "\r"),
        ("pause, a built-in waiting for a key", "pause\r"),
        ("(a key)", "x"),
        ("set /p, a built-in waiting for a line", "set /p NAME=Name: \r"),
        ("(a line)", "Ada\r"),
        ("set /p ending with >", "set /p NAME=Name> \r"),
        ("(a line)", "Ada\r"),
        ("timeout, a program waiting", "timeout /t 3 /nobreak >nul\r"),
        ("(wait for the end of timeout)", ""),
        ("(wait for the end of timeout)", ""),
        ("at the prompt again", ""),
    ],
    "powershell": [
        ("at the prompt", ""),
        ("Start-Sleep, a cmdlet running", "Start-Sleep 4\r"),
        ("(wait)", ""),
        ("Read-Host, a cmdlet waiting", "Read-Host 'Name'\r"),
        ("(a line)", "Ada\r"),
        ("ping, running", "ping -n 6 127.0.0.1 | Out-Null\r"),
        ("(wait)", ""),
        ("at the prompt again", ""),
    ],
}
PROGRAMS = {"cmd": "cmd.exe", "powershell": "powershell.exe"}


def drain(pty: winpty.PTY, model: PyteScreenModel, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        text = str(pty.read(blocking=False))
        if text:
            model.feed(text.encode("utf-8"))
        else:
            time.sleep(0.02)


def cursor_line(model: PyteScreenModel) -> str:
    update = model.take_update()
    rows = {row.number: row.text for row in update.rows}
    return rows.get(update.cursor_row, "?")


def main(name: str) -> int:
    program = PROGRAMS[name]
    pty = winpty.PTY(COLUMNS, ROWS, backend=winpty.Backend.ConPTY)
    path = Path(shutil.which(program) or program)
    pty.spawn(str(path), cwd=str(Path.cwd()))
    tree = ProcessTree(pty.pid)
    model = PyteScreenModel(COLUMNS, ROWS)
    drain(pty, model, 3.0)
    print(f"{name}: situation -> active processes | line of the cursor")
    cache: dict[int, str] = {}
    for label, typed in SITUATIONS[name]:
        if typed:
            pty.write(typed)
        drain(pty, model, SETTLE)
        update = model.take_update()
        cache.update({row.number: row.text for row in update.rows})
        line = cache.get(update.cursor_row, "?")
        print(f"  {label:42} -> {tree.active_processes()} | {line!r}")
    tree.terminate()
    tree.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "cmd"))
