"""Test program: output that arrives at a steady pace while the user reads.

Writes 60 lines, one every half second (30 seconds), each flushed at once so that it reaches the
application alone, even with pipes. A line starts with its number out of the total, then always
the same fruits, so that only the number tells two lines apart. The last line gives the time
really taken. The program ends by itself with the code 0; Stop the program interrupts it.
"""

import time

from _common import say, start

NAME = "Cadence"
LINES = 60
DELAY = 0.5  # seconds between two lines
TEXT = "Cerise Date Figue Jujube Kiwi Litchi Mangue Nèfle Pomme"


def main() -> int:
    start(NAME)
    began = time.monotonic()
    for number in range(1, LINES + 1):
        say(f"{number:02d}/{LINES} {TEXT}")
        time.sleep(DELAY)
    say(f"Fin : {LINES} lignes en {time.monotonic() - began:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
