"""Test program: web addresses, mail addresses, things that look like them, and a question.

Starts like every test program (see ``_common.py``). Then, under level 2 Markdown titles:

1. Web addresses: alone, in a sentence with signs around them, in parentheses, ``www.`` alone, and
   two on one line.
2. Mail addresses: alone, with ``+`` and dots, two on one line, and one inside a web address.
3. Traps that are neither: ``user@host`` (no dot), an address of ssh (``git@github.com:...``),
   version numbers.
4. A question, ``Continuer ? [O/n]``, with a mail address written **below** it. In "Identify
   activities" (Shift+F4) the list must open on the question, not on that last address.

In a CLI the program reads a whole line; in a TUI it reads the keys up to Enter. It ends by itself
with the code 0, whatever the answer.
"""

import msvcrt  # Windows only, like the application
import sys

from _common import say, start

NAME = "Addresses"
ENTER = "\r"


def web_addresses() -> None:
    say("## Adresses web")
    say("Documentation : https://example.org/aide/index.html")
    say("Voir la page (https://fr.wikipedia.org/wiki/Python_(langage)) pour plus.")
    say("Une phrase finie par une adresse, https://example.org/fin.")
    say("Sans protocole : www.exemple.fr")
    say("Deux sur une ligne : http://a.example.org/x et https://b.example.org/y?z=1#t")


def mail_addresses() -> None:
    say("## Adresses mail")
    say("Écrire à contact@exemple.org, merci.")
    say("Avec signe et points : prenom.nom+liste@mail.exemple.org")
    say("Deux sur une ligne : a@exemple.fr et b@exemple.fr")
    say("Dans une adresse web (une seule adresse) : https://utilisateur@exemple.org/profil")


def traps() -> None:
    say("## Pièges : ni adresse web ni adresse mail")
    say("Invite : utilisateur@machine")
    say("Dépôt ssh : git@github.com:utilisateur/depot.git")
    say("Versions : v1.2.3 et 3.5")


def read_answer(terminal: bool) -> str | None:
    """In a TUI the keys up to Enter; in a CLI a whole line. ``None`` when the input ends."""
    if not terminal:
        line = sys.stdin.readline()
        return line.rstrip("\r\n") if line else None
    typed = ""
    while True:
        character = msvcrt.getwch()
        if character == ENTER:
            say("")
            return typed
        if character == "\x04":  # Ctrl+D
            return None
        if character.isprintable():
            typed += character
            sys.stdout.write(character)
            sys.stdout.flush()


def question_with_an_address_below(terminal: bool) -> None:
    say("## Une question, avec une adresse en dessous")
    say("Continuer ? [O/n]")
    say("Aide : assistance@exemple.org")  # below the question: it must not take its place
    answer = read_answer(terminal)
    say("Fin de l'entrée." if answer is None else f"Réponse : {answer or 'oui (le défaut)'}")


def main() -> int:
    terminal = start(NAME)
    web_addresses()
    mail_addresses()
    traps()
    question_with_an_address_below(terminal)
    say("Fin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
