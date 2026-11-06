"""Default implementation of the output filter contract (see ``specs/robustness.md``).

It works like the line of a terminal: a carriage return moves back to the start of the line and
what follows overwrites it. When the shown part of the line changes, the whole line is handed out
again with ``replaces_current_line``; otherwise only the new characters are appended.
"""

from n5terminal.core.screen.output_filter import (
    CarriageReturnPolicy,
    FilteredChunk,
    FilterRules,
    RemovedAction,
)

ESC = "\x1b"
BEL = "\x07"
CR = "\r"
LF = "\n"
C1_CSI = "\x9b"
C1_STRING_TERMINATOR = "\x9c"
# Introducers of the sequences that run up to a string terminator: OSC, DCS, SOS, PM, APC.
C1_STRING_INTRODUCERS = frozenset("\x9d\x90\x98\x9e\x9f")
ESC_STRING_INTRODUCERS = frozenset("]PX^_")
MAX_SEQUENCE = 4096  # an unfinished sequence longer than this is dropped
DIRECTION_MARKS = frozenset(chr(code) for code in (*range(0x202A, 0x202F), *range(0x2066, 0x206A)))
ZERO_WIDTH = frozenset({"​", "﻿"})


class DefaultOutputFilter:
    """Applies :class:`FilterRules` to the output of one stream of one session.

    When ``strip_escape_sequences`` is false, ESC is handled like any other control character.
    """

    def __init__(self, rules: FilterRules | None = None) -> None:
        self._rules = rules if rules is not None else FilterRules()
        self._pending = ""
        self._line: list[str] = []
        self._column = 0
        self._shown = 0  # characters of the line already handed out
        self._rewritten = False  # a shown character of the line changed
        self._appended: list[str] = []
        self._chunks: list[FilteredChunk] = []

    def feed(self, text: str) -> list[FilteredChunk]:
        text = self._pending + text
        self._pending = ""
        index = 0
        while index < len(text):
            index = self._step(text, index)
        return self._hand_out()

    def finish(self) -> list[FilteredChunk]:
        if self._pending.startswith(ESC) or self._pending[:1] in C1_STRING_INTRODUCERS:
            self._remove()
        self._pending = ""
        return self._hand_out()

    def _step(self, text: str, index: int) -> int:
        char = text[index]
        if char == CR:
            return self._carriage_return(text, index)
        if char == LF and LF in self._rules.kept:
            self._line_feed()
            return index + 1
        if self._starts_sequence(char):
            return self._sequence(text, index)
        if self._is_removed(char):
            self._remove()
        else:
            self._put(char)
        return index + 1

    def _carriage_return(self, text: str, index: int) -> int:
        if index + 1 == len(text):
            self._pending = CR  # a line feed may follow in the next piece
            return index + 1
        if text[index + 1] == LF:
            self._line_feed()
            return index + 2
        if self._rules.carriage_return is CarriageReturnPolicy.NEW_LINE:
            self._line_feed()
        else:
            self._column = 0
        return index + 1

    def _starts_sequence(self, char: str) -> bool:
        if not self._rules.strip_escape_sequences:
            return False
        return char in (ESC, C1_CSI) or char in C1_STRING_INTRODUCERS

    def _sequence(self, text: str, index: int) -> int:
        end = _sequence_end(text, index)
        if end is None:
            if len(text) - index > MAX_SEQUENCE:
                self._remove()
            else:
                self._pending = text[index:]
            return len(text)
        self._remove()
        return end

    def _is_removed(self, char: str) -> bool:
        rules = self._rules
        code = ord(char)
        if char in rules.kept:
            return False
        if code < 0x20 or code == 0x7F:
            return True
        if 0x80 <= code <= 0x9F:
            return rules.strip_c1_controls
        if char in DIRECTION_MARKS:
            return rules.strip_direction_marks
        return char in ZERO_WIDTH and rules.strip_zero_width

    def _remove(self) -> None:
        if self._rules.on_removed is RemovedAction.MARK:
            self._put(self._rules.mark)

    def _put(self, char: str) -> None:
        if self._column < len(self._line):
            if self._line[self._column] != char:
                self._line[self._column] = char
                self._rewritten = self._rewritten or self._column < self._shown
        else:
            self._line.append(char)
        self._column += 1

    def _line_feed(self) -> None:
        self._flush_line()
        self._appended.append(LF)
        self._line = []
        self._column = 0
        self._shown = 0

    def _flush_line(self) -> None:
        if self._rewritten:
            self._close_appended()
            self._chunks.append(FilteredChunk("".join(self._line), replaces_current_line=True))
        else:
            self._appended.append("".join(self._line[self._shown :]))
        self._shown = len(self._line)
        self._rewritten = False

    def _close_appended(self) -> None:
        text = "".join(self._appended)
        self._appended = []
        if text:
            self._chunks.append(FilteredChunk(text))

    def _hand_out(self) -> list[FilteredChunk]:
        self._flush_line()
        self._close_appended()
        chunks = self._chunks
        self._chunks = []
        return chunks


def _sequence_end(text: str, start: int) -> int | None:
    """Index just after the escape sequence starting at ``start``; ``None`` when unfinished."""
    char = text[start]
    if char == C1_CSI:
        return _csi_end(text, start + 1)
    if char in C1_STRING_INTRODUCERS:
        return _string_end(text, start + 1)
    if start + 1 == len(text):
        return None
    introducer = text[start + 1]
    if introducer == "[":
        return _csi_end(text, start + 2)
    if introducer in ESC_STRING_INTRODUCERS:
        return _string_end(text, start + 2)
    return _escape_end(text, start + 1)


def _csi_end(text: str, index: int) -> int | None:
    """Parameters and intermediates (0x20 to 0x3F), then a final byte (0x40 to 0x7E)."""
    while index < len(text):
        char = text[index]
        if "\x40" <= char <= "\x7e":
            return index + 1
        if not "\x20" <= char <= "\x3f":
            return index  # malformed: the sequence stops before this character
        index += 1
    return None


def _string_end(text: str, index: int) -> int | None:
    """A string ended by BEL, by ST (ESC backslash) or by the C1 string terminator."""
    while index < len(text):
        char = text[index]
        if char in (BEL, C1_STRING_TERMINATOR):
            return index + 1
        if char == ESC:
            if index + 1 == len(text):
                return None
            return index + 2 if text[index + 1] == "\\" else index
        index += 1
    return None


def _escape_end(text: str, index: int) -> int | None:
    """Intermediates (0x20 to 0x2F), then one final character."""
    while index < len(text):
        if not "\x20" <= text[index] <= "\x2f":
            return index + 1
        index += 1
    return None
