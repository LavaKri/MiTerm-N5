"""Test program: what does the application send to a program, text or keys?

Starts like every test program (see ``_common.py``): its name as a level 1 Markdown title, then the
mode it detected, CLI (pipes) or TUI (console). Then, endlessly: a prompt (a level 2 Markdown
title), then the answer, either the text received or the name of the key received (with its
codes). Enter alone is a line break. Ctrl+D ends the program in a TUI, the end of the input in a
CLI.

In a CLI the program reads whole lines, so only text and line breaks can arrive. In a TUI it reads
the keys one by one: a key that is not a character is named at once, a character starts a text that
Enter ends.
"""

import msvcrt  # Windows only, like the application
import sys

from _common import say, start

ENTER = "\r"
EXTENDED_PREFIXES = ("\x00", "\xe0")
EXTENDED_KEYS = {
    "H": "Flèche haut",
    "P": "Flèche bas",
    "K": "Flèche gauche",
    "M": "Flèche droite",
    "G": "Début",
    "O": "Fin",
    "I": "Page précédente",
    "Q": "Page suivante",
    "R": "Insertion",
    "S": "Suppression",
    "\x0f": "Maj+Tab",
    "\x85": "F11",
    "\x86": "F12",
    **{chr(code): f"F{code - 58}" for code in range(59, 69)},  # F1 to F10
}
SIMPLE_KEYS = {
    "\r": "Entrée (saut de ligne)",
    "\t": "Tab",
    "\x1b": "Échap",
    "\x08": "Retour arrière",
    "\x7f": "Retour arrière",
    " ": "Espace",
}
QUIT_KEY = "\x04"  # Ctrl+D


def codes(text: str) -> str:
    return " ".join(f"{ord(character):02x}" for character in text)


def key_name(first: str, second: str = "") -> str:
    """The name of a key from the characters it sent."""
    if first in EXTENDED_PREFIXES:
        return EXTENDED_KEYS.get(second, f"Touche étendue {second!r}")
    if first in SIMPLE_KEYS:
        return SIMPLE_KEYS[first]
    if "\x01" <= first <= "\x1a":
        return f"Ctrl+{chr(ord(first) + 64)}"
    return f"Caractère {first!r}"


def read_key_or_text() -> tuple[str, str] | None:
    """In a TUI: ``("key", name)`` or ``("text", text)``; ``None`` to quit."""
    first = msvcrt.getwch()
    if first == QUIT_KEY:
        return None
    if first in EXTENDED_PREFIXES:
        second = msvcrt.getwch()
        return "key", f"{key_name(first, second)} [{codes(first + second)}]"
    if first in SIMPLE_KEYS or not first.isprintable():
        return "key", f"{key_name(first)} [{codes(first)}]"
    typed = first
    sys.stdout.write(first)
    sys.stdout.flush()
    while True:
        character = msvcrt.getwch()
        if character == ENTER:
            say("")
            return "text", typed
        if character == QUIT_KEY:
            return None
        if character in ("\x08", "\x7f"):
            typed = typed[:-1]
            sys.stdout.write("\x08 \x08")
        elif character.isprintable():
            typed += character
            sys.stdout.write(character)
        sys.stdout.flush()


def read_line() -> tuple[str, str] | None:
    """In a CLI: a whole line; ``None`` at the end of the input."""
    line = sys.stdin.readline()
    if not line:
        return None
    text = line.rstrip("\r\n")
    return ("key", "Entrée (saut de ligne)") if not text else ("text", text)


def main() -> int:
    terminal = start("Commands")
    quit_help = "Ctrl+D pour finir" if terminal else "fin de l'entrée pour finir"
    while True:
        say(f"## Entrez une commande ou une combinaison de touches ({quit_help})")
        received = read_key_or_text() if terminal else read_line()
        if received is None:
            say("Fin.")
            return 0
        kind, value = received
        say(f"Texte reçu : {value}" if kind == "text" else f"Touche reçue : {value}")


if __name__ == "__main__":
    raise SystemExit(main())
