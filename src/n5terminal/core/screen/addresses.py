"""The web addresses and the mail addresses written in a line of the output.

Used by "Identify activities" (``screen_elements.py``): unlike the analysis of a line, which makes
one element of it, a line can hold several addresses, each one an element. A pure function of the
text. The rules are plain on purpose: a start (``http://``, ``https://``, ``www.``) and the signs
that end an address; ``user@host`` with no dot, or ``git@github.com:user/repo`` (an address of ssh),
is not a mail address.
"""

import re
from dataclasses import dataclass

from n5terminal.core.screen.line_analysis import ElementKind

_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"'`]+", re.IGNORECASE)
_EMAIL = re.compile(r"(?<![\w.%+-])[\w.%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?![\w-])")
_END_SIGNS = ".,;:!?'\"]}>"


@dataclass(slots=True, frozen=True)
class Address:
    """An address: where it starts in the line, what it is and its text."""

    start: int
    kind: ElementKind
    text: str


def _trimmed(url: str) -> str:
    """``url`` without the signs of the sentence around it (``(see http://a.fr/x).``)."""
    while url:
        if url[-1] in _END_SIGNS or (url[-1] == ")" and url.count(")") > url.count("(")):
            url = url[:-1]
        else:
            break
    return url


def find_addresses(line: str) -> list[Address]:
    """The web addresses and the mail addresses of ``line``, in the order they are written."""
    found: list[Address] = []
    taken: list[tuple[int, int]] = []
    for match in _URL.finditer(line):
        text = _trimmed(match.group())
        if text:
            found.append(Address(match.start(), ElementKind.URL, text))
            taken.append((match.start(), match.start() + len(text)))
    for match in _EMAIL.finditer(line):
        inside_url = any(start <= match.start() < end for start, end in taken)
        if not inside_url and line[match.end() : match.end() + 1] != ":":
            found.append(Address(match.start(), ElementKind.EMAIL, match.group()))
    return sorted(found, key=lambda address: address.start)
