"""What a terminal shows for a stream of VT text: pyte's history plus screen, as lines."""

import pyte

HISTORY = 1000


def screen_lines(text: str, columns: int = 80, rows: int = 24) -> list[str]:
    screen = pyte.HistoryScreen(columns, rows, history=HISTORY)
    pyte.Stream(screen).feed(text)
    history = ["".join(line[x].data for x in range(columns)) for line in screen.history.top]
    lines = [line.rstrip() for line in (*history, *screen.display)]
    while lines and not lines[-1]:
        lines.pop()
    return lines
