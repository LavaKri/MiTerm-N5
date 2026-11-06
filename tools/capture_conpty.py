"""Record what ConPTY emits for real programs (experiment of the mode 4 milestone).

Usage: ``.venv\\Scripts\\python.exe tools\\capture_conpty.py [NAME ...]``: every scenario, or only
the ones named (a capture is not rewritten unless asked for). Each scenario is written to
``tests/data/captures/<name>.vt`` (UTF-8, exactly the text pywinpty returned) with the terminal
size in the first line, so that the tests can replay it into pyte.
"""

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import winpty

COLUMNS = 80
ROWS = 24
POLL = 0.01
QUIET_END = 1.0  # seconds without output after the last input before the program is stopped
TIMEOUT = 15.0
CAPTURES = Path(__file__).parent.parent / "tests" / "data" / "captures"


@dataclass(frozen=True)
class Scenario:
    name: str
    arguments: tuple[str, ...]
    inputs: tuple[str, ...] = ()  # sent one by one, each after the output went quiet


PYTHON = sys.executable
# One line per way a program can mark text: VT reverse video, the reverse video attribute of the
# Windows console API, two colours only, and reverse video that runs to the edge (an erase to the
# end of the line while it is on). It tells whether pyte finds the lines in reverse video.
REVERSE_PROGRAM = (
    "import ctypes, sys\n"
    "kernel = ctypes.windll.kernel32\n"
    "handle = kernel.GetStdHandle(-11)\n"
    "print('plain line')\n"
    "print('\\x1b[7mvt reverse\\x1b[0m')\n"
    "sys.stdout.flush()\n"
    "kernel.SetConsoleTextAttribute(handle, 0x0007 | 0x4000)\n"
    "sys.stdout.write('win32 reverse'); sys.stdout.flush()\n"
    "kernel.SetConsoleTextAttribute(handle, 0x0007)\n"
    "print()\n"
    "print('\\x1b[30;47mcolours only\\x1b[0m')\n"
    "sys.stdout.write('\\x1b[7mto the edge\\x1b[K\\x1b[0m\\n')\n"
)
# Programs for the analysis of the lines (6f): what simple programs write in line, and what a few
# real tools write, so that the rules are tried on real bytes.
BAR_PROGRAM = (
    "import time\n"
    "for i in range(0, 101, 20):\n"
    "    print(f'\\rDownloading [{chr(35) * (i // 5):<20}] {i:3d} %', end='', flush=True)\n"
    "    time.sleep(0.15)\n"
    "print()\n"
)
TWO_BARS_PROGRAM = (
    "import sys, time\n"
    "sys.stdout.write('\\x1b[2J\\x1b[H')\n"
    "for i in range(0, 101, 25):\n"
    "    sys.stdout.write(f'\\x1b[1;1HDownload  {i:3d}%\\x1b[K')\n"
    "    sys.stdout.write(f'\\x1b[2;1HUnpack    {i // 2:3d}%\\x1b[K')\n"
    "    sys.stdout.write('\\x1b[4;1H'); sys.stdout.flush(); time.sleep(0.15)\n"
    "print('done')\n"
)
QUESTIONS_PROGRAM = (
    "import getpass\n"
    "answer = input('Overwrite the file? [y/N] ')\n"
    "name = input('Your name: ')\n"
    "secret = getpass.getpass('Password: ')\n"
    "print('got', answer, name, len(secret))\n"
)
NUMBERED_MENU_PROGRAM = (
    "print('Select an option:')\n"
    "for number, name in enumerate(('Alpha', 'Beta', 'Gamma'), start=1):\n"
    "    print(f'  {number}) {name}')\n"
    "choice = input('Choice [1-3]: ')\n"
    "print('chosen', choice)\n"
)
GLYPH_MENU_PROGRAM = (
    "print('? Pick a color')\nprint('\\x1b[36m> Red\\x1b[0m')\nprint('  Green')\nprint('  Blue')\n"
)
ERRORS_PROGRAM = (
    "import sys\n"
    "print('error: file not found', file=sys.stderr)\n"
    "print('warning: using the default')\n"
    "print('Access is denied.')\n"
    "raise ValueError('boom')\n"
)
SCENARIOS = (
    Scenario("echo", ("cmd.exe", "/c", "echo hello & echo world")),
    Scenario("bar_cr", (PYTHON, "-c", BAR_PROGRAM)),
    Scenario("two_bars", (PYTHON, "-c", TWO_BARS_PROGRAM)),
    Scenario("questions", (PYTHON, "-c", QUESTIONS_PROGRAM), ("y\r", "Ada\r", "secret\r")),
    Scenario("numbered_menu", (PYTHON, "-c", NUMBERED_MENU_PROGRAM), ("2\r",)),
    Scenario("glyph_menu", (PYTHON, "-c", GLYPH_MENU_PROGRAM)),
    Scenario("errors", (PYTHON, "-c", ERRORS_PROGRAM)),
    Scenario("pip_dry_run", (PYTHON, "-m", "pip", "install", "--dry-run", "--no-deps", "six")),
    Scenario("winget_search", ("winget.exe", "search", "--id", "Python.Python.3.12")),
    Scenario("many_lines", (PYTHON, "-c", "for i in range(60): print(f'line {i}')")),
    Scenario("long_line", (PYTHON, "-c", "print('x' * 200)")),
    Scenario(
        "progress",
        (
            PYTHON,
            "-c",
            "import time\nfor i in range(0, 101, 20):\n"
            "    print(f'\\r{i}%', end='', flush=True); time.sleep(0.2)\nprint()",
        ),
    ),
    Scenario("colors", (PYTHON, "-c", "print('\\x1b[31mred\\x1b[0m plain')")),
    Scenario("reverse", (PYTHON, "-c", REVERSE_PROGRAM)),
    Scenario("accents", (PYTHON, "-c", "print('é à ç € ✓')")),
    Scenario("python_repl", (PYTHON, "-i", "-q"), ("1 + 1\r", "print('hi')\r", "exit()\r")),
    Scenario("cmd_session", ("cmd.exe",), ("echo one\r", "cd\r", "exit\r")),
    Scenario("ssh_usage", ("ssh.exe",)),
)


def read_until_quiet(pty: winpty.PTY, parts: list[str], deadline: float) -> None:
    last = time.monotonic()
    while time.monotonic() < deadline:
        try:
            text = pty.read(blocking=False)
        except winpty.WinptyError:  # the pseudo console closed: the program has ended (winget)
            return
        if text:
            parts.append(text)
            last = time.monotonic()
        elif not pty.isalive() or time.monotonic() - last > QUIET_END:
            return
        time.sleep(POLL)


def capture(scenario: Scenario) -> str:
    program = shutil.which(scenario.arguments[0])
    if program is None:
        return ""
    pty = winpty.PTY(COLUMNS, ROWS, backend=winpty.Backend.ConPTY)
    command_line = " ".join(_quote(argument) for argument in scenario.arguments[1:])
    pty.spawn(program, cmdline=f" {command_line}" if command_line else None, cwd=str(Path.cwd()))
    deadline = time.monotonic() + TIMEOUT
    parts: list[str] = []
    read_until_quiet(pty, parts, deadline)
    for line in scenario.inputs:
        pty.write(line)
        read_until_quiet(pty, parts, deadline)
    print(f"{scenario.name}: alive={pty.isalive()} exit={pty.get_exitstatus()}")
    return "".join(parts)


def _quote(argument: str) -> str:
    return subprocess.list2cmdline([argument])


def main(names: list[str]) -> int:
    CAPTURES.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        if names and scenario.name not in names:
            continue
        text = capture(scenario)
        if not text:
            print(f"{scenario.name}: not available, skipped")
            continue
        path = CAPTURES / f"{scenario.name}.vt"
        path.write_text(f"{COLUMNS}x{ROWS}\n{text}", encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
