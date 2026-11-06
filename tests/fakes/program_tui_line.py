"""A line-oriented program that needs a real terminal (mode 4), driven by a scenario.

Usage: ``python program_tui_line.py SCENARIO [CODE]``. Refuses to run without a terminal, as many
interactive programs do, so the same program tells the pipe mode and the terminal mode apart.
"""

import getpass
import os
import sys
import time

LONG_SLEEP = 60
SIZE_WAIT = 5.0  # seconds the "size" scenario waits for a resize to arrive
SIZE_POLL = 0.02


def terminal() -> int:
    print("terminal: yes")
    print("\x1b[31mred\x1b[0m plain", flush=True)
    return 0


def echo_input() -> int:
    line = input("name? ")
    print(f"got: {line}", flush=True)
    return 0


def password() -> int:
    secret = getpass.getpass("password: ")
    print(f"length {len(secret)}", flush=True)
    return 0


def size() -> int:
    """Say the size of the terminal once the input came and the size changed (or SIZE_WAIT passed).

    A pseudo console applies a resize on its own time: the size read right after the input can still
    be the old one. Waiting for the change, not for a fixed time, keeps the test steady; if the
    resize never arrives the old size is said, and the test fails for the right reason.
    """
    before = os.get_terminal_size()
    input("ready? ")
    deadline = time.monotonic() + SIZE_WAIT
    current = os.get_terminal_size()
    while current == before and time.monotonic() < deadline:
        time.sleep(SIZE_POLL)
        current = os.get_terminal_size()
    print(f"size {current.columns}x{current.lines}", flush=True)
    return 0


def sleep() -> int:
    time.sleep(LONG_SLEEP)
    return 0


def main(arguments: list[str]) -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("not a terminal", file=sys.stderr, flush=True)
        return 2
    scenario = arguments[0]
    if scenario == "exit":
        return int(arguments[1])
    scenarios = {
        "terminal": terminal,
        "echo-input": echo_input,
        "password": password,
        "size": size,
        "sleep": sleep,
    }
    return scenarios[scenario]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
