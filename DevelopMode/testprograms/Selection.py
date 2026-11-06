"""Test program: a list in which the user moves with the arrow keys (a TUI only).

Starts like every test program (see ``_common.py``). In a CLI it only says that it needs a
terminal. In a TUI it runs three lists one after the other, each drawn on a cleared screen by
positioning the cursor, and moved with Up, Down, Page up, Page down, Home and End; Enter chooses,
then Enter goes on to the next list.

1. A marker ``>`` in front of the chosen line, rewritten as the choice moves.
2. No marker at all: the cursor of the terminal is on the chosen line (the commands to reach it are
   in the Move menu).
3. A long list of thirty lines of which eight show, with a counter ("3/30") under them: the window
   slides, so many rows are rewritten at once.

The program ends by itself with the code 0.
"""

import msvcrt  # Windows only, like the application
import sys

from _common import enable_escape_sequences, say, start

NAME = "Selection"
CLEAR = "\x1b[2J\x1b[H"
ERASE_END_OF_LINE = "\x1b[K"
EXTENDED_PREFIXES = ("\x00", "\xe0")
EXTENDED_KEYS = {"H": "up", "P": "down", "I": "page_up", "Q": "page_down", "G": "home", "O": "end"}
ENTER = "\r"
FRUITS = ("Cerise", "Date", "Figue", "Jujube", "Kiwi", "Litchi", "Mangue", "Nèfle")
LONG_LIST = tuple(f"Élément {number:02d}" for number in range(1, 31))
WINDOW = 8  # rows of a long list that show
PAGE = WINDOW - 1


def read_key() -> str:
    """The name of the next key: a move, ``enter`` or ``other``."""
    first = msvcrt.getwch()
    if first in EXTENDED_PREFIXES:
        return EXTENDED_KEYS.get(msvcrt.getwch(), "other")
    return "enter" if first == ENTER else "other"


def moved(selected: int, key: str, count: int) -> int:
    """The index chosen after ``key``, kept inside the list."""
    target = {
        "up": selected - 1,
        "down": selected + 1,
        "page_up": selected - PAGE,
        "page_down": selected + PAGE,
        "home": 0,
        "end": count - 1,
    }.get(key, selected)
    return min(max(target, 0), count - 1)


def draw(lines: list[str], cursor_row: int) -> None:
    """Write each line on its row of the screen, then put the cursor on ``cursor_row``."""
    text = "".join(f"\x1b[{row};1H{line}{ERASE_END_OF_LINE}" for row, line in enumerate(lines, 1))
    sys.stdout.write(f"{text}\x1b[{cursor_row};1H")
    sys.stdout.flush()


def choose(title: str, items: tuple[str, ...], *, marker: bool, window: int, counter: bool) -> str:
    """Let the user choose an item; the item chosen."""
    sys.stdout.write(CLEAR)
    selected = top = 0
    while True:
        top = min(max(top, selected - window + 1), selected)
        shown = range(top, min(top + window, len(items)))
        lines = [title]
        lines.extend(
            f"{'> ' if marker and index == selected else '  '}{items[index]}" for index in shown
        )
        if counter:
            lines.append(f"{selected + 1}/{len(items)}")
        # With a marker the cursor waits under the list; without, it is on the chosen line.
        cursor_row = len(lines) + 2 if marker else 2 + selected - top
        draw(lines, cursor_row)
        key = read_key()
        if key == "enter":
            return items[selected]
        selected = moved(selected, key, len(items))


def finish_list(item: str, below: int) -> None:
    """Say the choice under the list, and wait for Enter before the next list."""
    sys.stdout.write(f"\x1b[{below};1H")
    say(f"Choisi : {item}")
    say("Entrée pour passer à la suite.")
    while read_key() != "enter":
        pass


def main() -> int:
    if not start(NAME):
        say("Ce programme demande un terminal : lancez-le en mode TUI.")
        return 0
    enable_escape_sequences()
    marked = choose("## Avec un marqueur >", FRUITS, marker=True, window=WINDOW, counter=False)
    finish_list(marked, len(FRUITS) + 4)
    bare = choose(
        "## Sans marqueur : le curseur du terminal est sur le choix",
        FRUITS,
        marker=False,
        window=WINDOW,
        counter=False,
    )
    finish_list(bare, len(FRUITS) + 4)
    long = choose(
        "## Liste longue qui défile",
        LONG_LIST,
        marker=True,
        window=WINDOW,
        counter=True,
    )
    finish_list(long, WINDOW + 5)
    say("Fin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
