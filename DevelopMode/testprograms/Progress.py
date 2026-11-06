"""Test program: progress bars that are rewritten in place while the user reads.

Starts like every test program (see ``_common.py``). Then it depends on the mode it detected.

In a CLI (pipes), three bars one after the other, 20 seconds each, rewritten with a carriage return:
a download bar on the standard error, a verification bar on the standard output between lines of
text, and an installation bar on the standard output that never ends its line (the program ends on
``100 %``).

In a TUI (console), the screen is cleared and drawn by positioning the cursor: one bar on the first
row for 30 seconds, then, after a pause, two bars on the first and second rows, the slowest taking
30 seconds. The cursor is parked under the bars. The program ends by itself with the code 0; Stop
the program interrupts it.
"""

import sys
import time
from typing import TextIO

from _common import enable_escape_sequences, say, start

NAME = "Progress"
WIDTH = 30  # characters of a bar
STEPS = 100  # one per percent
CLI_SECONDS = 20.0
TUI_SECONDS = 30.0
TUI_FAST_SECONDS = 20.0
SETTLE = 0.3  # seconds before a CLI bar starts
PAUSE = 3.0  # seconds between the two TUI scenarios
TICK = 0.2  # seconds between two redraws in a TUI
CLEAR = "\x1b[2J"
ERASE_END_OF_LINE = "\x1b[K"


def bar(label: str, percent: int) -> str:
    filled = WIDTH * percent // 100
    return f"{label} [{'#' * filled}{'.' * (WIDTH - filled)}] {percent:3d} %"


def pace(began: float, step: int, seconds: float) -> None:
    """Wait until ``step`` out of ``STEPS`` is due, so that the delays do not add up."""
    time.sleep(max(0.0, began + step * seconds / STEPS - time.monotonic()))


# CLI ---------------------------------------------------------------------------------------------


def cli_bar(label: str, seconds: float, stream: TextIO, *, end_line: bool) -> None:
    """Rewrite a bar on ``stream`` with a carriage return, one percent at a time."""
    # The two streams are two pipes read by two threads: what was written just before on the other
    # one may be read after the bar starts. A short wait keeps the test about the bars.
    time.sleep(SETTLE)
    began = time.monotonic()
    for step in range(STEPS + 1):
        stream.write(f"\r{bar(label, step)}")
        stream.flush()
        if step < STEPS:
            pace(began, step + 1, seconds)
    if end_line:
        stream.write("\n")
        stream.flush()


def cli() -> None:
    say("## Téléchargement (sortie d'erreur, 20 s)")
    cli_bar("Téléchargement", CLI_SECONDS, sys.stderr, end_line=True)
    say("## Vérification (sortie standard, au milieu du texte, 20 s)")
    say("Ligne de texte avant la barre.")
    cli_bar("Vérification", CLI_SECONDS, sys.stdout, end_line=True)
    say("Ligne de texte après la barre.")
    say("## Installation (sortie standard, sans saut de ligne à la fin, 20 s)")
    cli_bar("Installation", CLI_SECONDS, sys.stdout, end_line=False)


# TUI ---------------------------------------------------------------------------------------------


def draw(rows: list[tuple[str, int]], parked_row: int) -> None:
    """Write each bar on its row, then park the cursor under them."""
    text = "".join(
        f"\x1b[{row};1H{bar(label, percent)}{ERASE_END_OF_LINE}"
        for row, (label, percent) in enumerate(rows, start=1)
    )
    sys.stdout.write(f"{text}\x1b[{parked_row};1H")
    sys.stdout.flush()


def tui_bars(bars: list[tuple[str, float]]) -> float:
    """Run bars on the first rows of a cleared screen until the slowest is done; seconds taken."""
    sys.stdout.write(f"{CLEAR}\x1b[H")
    parked_row = len(bars) + 2
    began = time.monotonic()
    shown: list[tuple[str, int]] = []
    while True:
        elapsed = time.monotonic() - began
        current = [(label, min(STEPS, int(elapsed / seconds * STEPS))) for label, seconds in bars]
        if current != shown:
            draw(current, parked_row)
            shown = current
        if all(percent == STEPS for _label, percent in current):
            return elapsed
        time.sleep(TICK)


def tui() -> None:
    enable_escape_sequences()
    taken = tui_bars([("Téléchargement", TUI_SECONDS)])
    say(f"Fin : une barre en {taken:.1f} s")
    time.sleep(PAUSE)
    taken = tui_bars([("Téléchargement", TUI_SECONDS), ("Décompression ", TUI_FAST_SECONDS)])
    say(f"Fin : deux barres en {taken:.1f} s")


def main() -> int:
    terminal = start(NAME)
    if terminal:
        tui()
    else:
        cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
