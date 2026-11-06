"""Replay the ConPTY captures into a pyte ``HistoryScreen`` and print the lines it holds.

Usage: ``.venv\\Scripts\\python.exe tools\\replay_captures.py [name ...]``. Experiment of the mode 4
milestone: shows what reading pyte's history plus screen gives for each captured program.
"""

import sys
from pathlib import Path

import pyte

CAPTURES = Path(__file__).parent.parent / "tests" / "data" / "captures"
HISTORY = 1000


def replay(path: Path) -> list[str]:
    size, _, text = path.read_text(encoding="utf-8", newline="").partition("\n")
    columns, rows = (int(value) for value in size.split("x"))
    screen = pyte.HistoryScreen(columns, rows, history=HISTORY)
    stream = pyte.Stream(screen)
    stream.feed(text)
    history = ["".join(line[x].data for x in range(columns)) for line in screen.history.top]
    lines = [line.rstrip() for line in (*history, *screen.display)]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def main(names: list[str]) -> int:
    paths = [CAPTURES / f"{name}.vt" for name in names] or sorted(CAPTURES.glob("*.vt"))
    for path in paths:
        print(f"===== {path.stem}")
        for number, line in enumerate(replay(path), 1):
            print(f"{number:3} |{line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
