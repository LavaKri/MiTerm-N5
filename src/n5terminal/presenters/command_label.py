"""How a block of several lines is kept, read and sent.

A block is a command text with line breaks (typed in the multi-line input, see "Multi-line input"
in ``specs/interface.md``). It is one entry of the history, with its real line breaks; the list of
Ctrl+Space reads it as its first line, shortened, and its number of lines.
"""

from collections.abc import Callable

from n5terminal.i18n import N_

#: The longest first line a block shows in the list of commands (the rest is cut with an ellipsis).
MAX_LABEL = 50
BLOCK_FORMAT = N_("{text} ({count} lines)")

Translate = Callable[[str], str]


def normalize_block(text: str) -> str:
    """``text`` with ``\\n`` as its only line break and no empty line at the end.

    A text with no line break is returned as it is.
    """
    if "\n" not in text and "\r" not in text:
        return text
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def is_block(text: str) -> bool:
    """Does ``text`` hold several lines?"""
    return "\n" in text


def command_label(text: str, translate: Translate) -> str:
    """What the list of commands reads for ``text``.

    A single line is read as it is. A block is read as its first line, cut at ``MAX_LABEL``
    characters, and its number of lines (``foreach ($x in 1..3) { (4 lines)``).
    """
    if not is_block(text):
        return text
    lines = text.split("\n")
    first = lines[0]
    if len(first) > MAX_LABEL:
        first = first[:MAX_LABEL].rstrip() + "…"
    return translate(BLOCK_FORMAT).format(text=first, count=len(lines))
