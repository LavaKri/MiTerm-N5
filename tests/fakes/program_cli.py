"""A command-line program driven by a scenario, run by the tests through the real pipe transport.

Usage: ``python -u program_cli.py SCENARIO [COUNT]``. It depends on no program of the system.
"""

import subprocess
import sys
import time

SPLIT_PAUSE = 0.1
LONG_SLEEP = 60


def both_streams() -> int:
    """Write on stdout and stderr, then fail with exit code 3."""
    sys.stdout.write("out\n")
    sys.stderr.write("err\n")
    return 3


def echo_input() -> int:
    """Answer every line read on stdin until "quit"."""
    for line in sys.stdin:
        text = line.rstrip("\n")
        if text == "quit":
            return 0
        print(f"got: {text}", flush=True)
    return 0


def flood(count: int) -> int:
    """Write ``count`` lines as fast as possible."""
    for number in range(count):
        print(f"line {number}")
    return 0


def split_character() -> int:
    """Write a two-byte UTF-8 character in two separate writes."""
    data = "é".encode()
    sys.stdout.buffer.write(data[:1])
    sys.stdout.buffer.flush()
    time.sleep(SPLIT_PAUSE)
    sys.stdout.buffer.write(data[1:])
    sys.stdout.buffer.flush()
    return 0


def sleep() -> int:
    """Never end by itself: the test stops it."""
    time.sleep(LONG_SLEEP)
    return 0


def start_child() -> None:
    """Start a copy that never ends and holds the same output pipes."""
    subprocess.Popen(
        [sys.executable, __file__, "sleep"],
        stdin=subprocess.DEVNULL,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print("child started", flush=True)


def child_and_wait() -> int:
    """Start a child, then never end."""
    start_child()
    return sleep()


def child_and_end() -> int:
    """Start a child, then end at once, leaving the child behind."""
    start_child()
    return 0


def main(arguments: list[str]) -> int:
    scenario = arguments[0]
    if scenario == "flood":
        return flood(int(arguments[1]))
    scenarios = {
        "both-streams": both_streams,
        "echo-input": echo_input,
        "split-character": split_character,
        "sleep": sleep,
        "child-and-wait": child_and_wait,
        "child-and-end": child_and_end,
    }
    return scenarios[scenario]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
