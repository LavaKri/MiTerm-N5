"""Replay the ConPTY captures through the screen model and print what the screen shows.

Usage: ``.venv\\Scripts\\python.exe tools\\replay_screens.py [--chunk 256] [name ...]``.
Experiment of 6f: for each capture, prints the lines that left the screen and the rows that changed
at each step, as the session would see them at each tick of the window (one chunk per tick), and
after each line the element the analysis of the line recognizes in it. This is how a rule is tried
on real programs. One line per fact, to be read with a screen reader.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))  # the captures and the replay

from fakes.capture_replay import DEFAULT_CHUNK, ReplayStep, replay
from fakes.captures import capture_names, load_capture
from n5terminal.core.screen.line_analysis import analyze_line


def recognized(text: str) -> str:
    """What the analysis of the line finds in ``text``, written after the line."""
    element = analyze_line(text)
    return f" -> {element.kind.name} {element.text!r}" if element else ""


def print_step(step: ReplayStep) -> None:
    if not step.changed:
        return
    update = step.update
    print(f"step {step.number}, {step.time:.2f} s: screen changed")
    for line in update.fixed:
        print(f"  fixed: {line.text!r}{recognized(line.text)}")
    for row in update.rows:
        if row.text or not update.replace_all:  # a new screen: only the rows with text
            print(f"  row {row.number}: {row.text!r}{recognized(row.text)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="replay_screens")
    parser.add_argument("names", nargs="*", help="the captures (default: all)")
    parser.add_argument("--chunk", type=int, default=DEFAULT_CHUNK, help="bytes per tick")
    arguments = parser.parse_args(argv)
    for name in arguments.names or capture_names():
        capture = load_capture(name)
        steps = replay(capture, arguments.chunk)
        print(f"===== {name} ({capture.columns}x{capture.rows}), {len(steps)} steps")
        for step in steps:
            print_step(step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
