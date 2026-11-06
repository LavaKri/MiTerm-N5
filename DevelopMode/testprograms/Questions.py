"""Test program: questions the program asks and answers the user gives.

Starts like every test program (see ``_common.py``). Then four questions, one after the other, each
under a level 2 Markdown title:

1. A yes or no question with a default: ``Continuer ? [O/n]``, Enter alone is yes.
2. A password: in a TUI nothing shows while it is typed; in a CLI the application sends the whole
   line. The program only says how many characters it received, never the password.
3. Numbered choices, with an answer out of the list that is asked again after an error message.
4. A question whose line is not ended (``Votre nom : ``): the answer goes on the same line.

In a CLI the program reads whole lines; in a TUI it reads the keys one by one, and Ctrl+D ends the
program. The end of the input ends it in a CLI. It ends by itself with the code 0.
"""

import msvcrt  # Windows only, like the application
import sys

from _common import say, start

NAME = "Questions"
ENTER = "\r"
BACKSPACES = ("\x08", "\x7f")
QUIT_KEY = "\x04"  # Ctrl+D
EXTENDED_PREFIXES = ("\x00", "\xe0")
YES = ("", "o", "oui", "y", "yes")
NO = ("n", "non", "no")
COLORS = ("Rouge", "Vert", "Bleu")


def read_typed(*, echo: bool) -> str | None:
    """In a TUI: the keys up to Enter (shown unless ``echo`` is false); ``None`` for Ctrl+D."""
    typed = ""
    while True:
        character = msvcrt.getwch()
        if character == ENTER:
            say("")
            return typed
        if character == QUIT_KEY:
            return None
        if character in EXTENDED_PREFIXES:
            msvcrt.getwch()  # the second code of a key such as an arrow: not text
        elif character in BACKSPACES:
            if typed:
                typed = typed[:-1]
                if echo:
                    sys.stdout.write("\x08 \x08")
        elif character.isprintable():
            typed += character
            if echo:
                sys.stdout.write(character)
        sys.stdout.flush()


def ask(question: str, *, terminal: bool, newline: bool = True, echo: bool = True) -> str | None:
    """Write ``question`` and read the answer; ``None`` when the input ends.

    The question ends its line when ``newline``; otherwise the answer goes on the same line.
    """
    if newline:
        say(question)
    else:
        sys.stdout.write(question)
        sys.stdout.flush()
    if terminal:
        return read_typed(echo=echo)
    line = sys.stdin.readline()
    return line.rstrip("\r\n") if line else None


def yes_or_no(terminal: bool) -> bool:
    say("## Oui ou non, avec un défaut")
    while True:
        answer = ask("Continuer ? [O/n]", terminal=terminal)
        if answer is None:
            return False
        lowered = answer.strip().lower()
        if lowered in YES:
            say("Réponse : oui" + (" (le défaut)" if not lowered else ""))
            return True
        if lowered in NO:
            say("Réponse : non")
            return True
        say(f"Erreur : « {answer} » n'est ni oui ni non.")


def password(terminal: bool) -> bool:
    say("## Mot de passe" + (" (rien ne s'affiche)" if terminal else ""))
    answer = ask("Mot de passe :", terminal=terminal, echo=False)
    if answer is None:
        return False
    say(f"Mot de passe reçu : {len(answer)} caractères")
    return True


def numbered_choice(terminal: bool) -> bool:
    say("## Choix numérotés")
    for number, color in enumerate(COLORS, 1):
        say(f"{number}) {color}")
    while True:
        answer = ask("Numéro :", terminal=terminal)
        if answer is None:
            return False
        if answer.strip().isdigit() and 1 <= int(answer) <= len(COLORS):
            say(f"Couleur choisie : {COLORS[int(answer) - 1]}")
            return True
        say(f"Erreur : « {answer} » n'est pas un numéro de 1 à {len(COLORS)}.")


def name_without_line_end(terminal: bool) -> bool:
    say("## Question sans saut de ligne")
    answer = ask("Votre nom : ", terminal=terminal, newline=False)
    if answer is None:
        return False
    say(f"Bonjour {answer}.")
    return True


def main() -> int:
    terminal = start(NAME)
    for question in (yes_or_no, password, numbered_choice, name_without_line_end):
        if not question(terminal):
            break
    say("Fin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
