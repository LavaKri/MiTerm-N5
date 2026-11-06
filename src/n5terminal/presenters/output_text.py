"""The text of the output area, and how each update changes it.

The area is made of a **fixed part** (the lines that will not change, which only grows) followed
by a **live part** (the unfinished line in CLI, the rows of the screen in TUI), see "One model for
every mode" in ``specs/interface.md``, and, at the end of a connection, by a **closing part** (the
line that says it ended). The closing part goes with the live part: the next output that replaces
the one empties it. This module keeps that text and turns an update of the screen
model into the smallest change of the text control, so that:
- a screen reader is not made to read again what did not change;
- the caret and the selection stay where they were (same line and column, else the start of the
  line), which makes the update silent. Output arriving never moves the caret.

Offsets are Python string indexes of a text that uses ``\\n`` as line break; the window converts
them to the positions of a Windows text field (``core/screen/titles.py``).
"""

from dataclasses import dataclass

from n5terminal.core.screen.screen_model import ScreenUpdate


def _common_length(first: str, second: str) -> int:
    """How many characters two texts have in common at their start."""
    count = 0
    for one, other in zip(first, second, strict=False):
        if one != other:
            break
        count += 1
    return count


@dataclass(slots=True, frozen=True)
class OutputEdit:
    """A change of the text, in the coordinates of the *old* text.

    Replace ``[start, end)`` by ``replacement``, then remove the first ``removed_head`` characters
    of the result (the oldest lines, past the limit). ``trimmed_lines`` says how many lines that
    was.
    """

    start: int
    end: int
    replacement: str
    removed_head: int = 0
    trimmed_lines: int = 0


class OutputText:
    """The fixed lines, the live rows, the closing lines, and the text they make."""

    def __init__(self, limit: int, *, show_history: bool = True) -> None:
        self._limit = limit
        self._show_history = show_history
        self._closing: list[str] = []  # the closing part, after the live part
        self._fixed: list[str] = []
        self._fixed_length = 0  # characters of the fixed lines, line breaks included
        self._rows: dict[int, str] = {}
        self._row_count = 0
        self._cursor = (0, 0)  # (row, column) of the terminal cursor in the live part
        self._tail = ""  # the live part as shown
        self._columns = 0  # the width of the terminal screen (0: with pipes there is none)
        self._text: str | None = ""

    @property
    def text(self) -> str:
        """The whole text, with ``\\n`` as line break."""
        if self._text is None:
            fixed = "".join(f"{line}\n" for line in self._fixed)
            self._text = fixed + self._tail + self._closing_text()
        return self._text

    @property
    def columns(self) -> int:
        """The width of the terminal screen, 0 when the program is served with pipes."""
        return self._columns

    @property
    def show_history(self) -> bool:
        return self._show_history

    def set_limit(self, limit: int) -> None:
        """Keep at most ``limit`` fixed lines (applied at the next update)."""
        self._limit = limit

    def set_show_history(self, show_history: bool) -> OutputEdit | None:
        """With history, the live part loses its blank rows at the end; without, it shows them all.

        Returns the change of the text, ``None`` if there is none.
        """
        self._show_history = show_history
        return self._rebuild_tail("")

    def apply(self, update: ScreenUpdate) -> OutputEdit | None:
        """Take an update of the screen model; the change of the text, ``None`` if there is none."""
        old_text, old_live_end = self.text, self.live_end_index()
        appended = self._append_fixed(update)
        removed_head, trimmed = self._trim()
        if update.replace_all:
            self._rows = {}
        self._rows.update({row.number: row.text for row in update.rows})
        if not (update.closing is not None and update.row_count == 0):  # else: no screen to tell
            self._row_count = update.row_count if update.replace_all else self._row_count
            if update.columns:  # the lines written by the application itself have no width
                self._columns = update.columns
            self._cursor = (update.cursor_row, update.cursor_column)
        edit = self._rebuild_tail(appended, removed_head, trimmed)
        if self._take_closing(update):
            return self._edit_to_the_end(len(old_text), old_live_end, edit, removed_head, trimmed)
        return edit

    def clear(self) -> OutputEdit | None:
        """Empty the text (the program goes on: its next update fills the live part again)."""
        old_length = len(self.text)
        self._fixed, self._fixed_length, self._closing = [], 0, []
        self._rows, self._row_count, self._tail, self._text = {}, 0, "", ""
        self._cursor = (0, 0)
        return OutputEdit(0, old_length, "") if old_length else None

    def live_start_index(self) -> int:
        """Where the live part (the emulator) begins in the text."""
        return self._fixed_length

    def fixed_line_start(self, back: int) -> int:
        """Where the ``back``-th fixed line from the end begins (0 if there are fewer lines)."""
        if back <= 0:
            return self._fixed_length
        return max(self._fixed_length - sum(len(line) + 1 for line in self._fixed[-back:]), 0)

    def live_end_index(self) -> int:
        """Where the live part ends: the end of the text, but for the closing part."""
        return self._fixed_length + len(self._tail)

    @property
    def has_closing(self) -> bool:
        """Is there a closing part?"""
        return bool(self._closing)

    def terminal_cursor_index(self) -> int:
        """Where the terminal cursor is in the text.

        The column is kept inside the row (a row loses its trailing blanks, so the cursor can be
        past its end). A cursor on a row that is not shown (the blank rows at the end with history)
        is at the end of the text.
        """
        rows = self._live_rows()
        row, column = self._cursor
        if row >= len(rows):
            return self.live_end_index()
        before = sum(len(text) + 1 for text in rows[:row])
        return self._fixed_length + before + min(column, len(rows[row]))

    def caret_after(self, index: int, edit: OutputEdit) -> int:
        """Where a caret at ``index`` of the old text is in the new one.

        Before the change: unchanged. After it: shifted. Inside: the same column of the same line,
        or the start of the line when the column no longer exists.
        """
        replaced = edit.end - edit.start
        if index < edit.start:
            new = index
        elif index >= edit.end:
            new = index - replaced + len(edit.replacement)
        else:
            new = edit.start + (index - edit.start)
            if new > edit.start + len(edit.replacement):
                end_of_change = edit.start + len(edit.replacement)
                new = self.text.rfind("\n", 0, end_of_change) + 1
        return max(new - edit.removed_head, 0)

    # Inside ------------------------------------------------------------------------------------

    def _append_fixed(self, update: ScreenUpdate) -> str:
        kept = update.columns == 0 or self._show_history  # a TUI without history drops them
        lines = [line.text for line in update.fixed] if kept else []
        self._fixed.extend(lines)
        added = "".join(f"{line}\n" for line in lines)
        self._fixed_length += len(added)
        return added

    def _trim(self) -> tuple[int, int]:
        """Drop the oldest fixed lines past the limit; (characters removed, lines removed)."""
        excess = len(self._fixed) - self._limit
        if excess <= 0:
            return 0, 0
        removed = sum(len(line) + 1 for line in self._fixed[:excess])
        del self._fixed[:excess]
        self._fixed_length -= removed
        return removed, excess

    def _closing_text(self) -> str:
        """The closing part as the text holds it: a line break after the live part, its lines."""
        return "\n" + "\n".join(self._closing) if self._closing else ""

    def _take_closing(self, update: ScreenUpdate) -> bool:
        """Take the closing lines of ``update``; whether the closing part changed.

        An update that says nothing empties it when it brings lines or replaces the live part: the
        output that follows is the next one.
        """
        if update.closing is not None:
            lines = [line.text for line in update.closing]
        elif update.fixed or update.replace_all:
            lines = []
        else:
            return False
        changed = lines != self._closing
        self._closing = lines
        self._text = None
        return changed

    def _edit_to_the_end(
        self,
        old_length: int,
        old_live_end: int,
        edit: OutputEdit | None,
        removed_head: int,
        trimmed_lines: int,
    ) -> OutputEdit:
        """The change from where the text first differs to its end, when the closing part changed.

        The closing part is after the live part, so one change covers both: from the start of the
        change of the live part (or the end of the old live part) to the old end of the text.
        ``old_live_end`` and ``old_length`` are in the coordinates of the old text.
        """
        start = min(edit.start, old_live_end) if edit is not None else old_live_end
        return OutputEdit(
            start=start,
            end=old_length,
            replacement=self.text[start - removed_head :],
            removed_head=removed_head,
            trimmed_lines=trimmed_lines,
        )

    def _live_rows(self) -> list[str]:
        rows = [self._rows.get(number, "") for number in range(self._row_count)]
        if self._show_history:
            while rows and not rows[-1]:
                rows.pop()
        return rows

    def _live_text(self) -> str:
        return "\n".join(self._live_rows())

    def _rebuild_tail(
        self, appended: str, removed_head: int = 0, trimmed_lines: int = 0
    ) -> OutputEdit | None:
        old_tail, new_tail = self._tail, self._live_text()
        replacement = appended + new_tail
        self._tail = new_tail
        self._text = None
        if replacement == old_tail and not removed_head:
            return None
        # Only the part that differs is replaced: what is common at the start and at the end stays.
        prefix = _common_length(old_tail, replacement)
        rest_old, rest_new = old_tail[prefix:], replacement[prefix:]
        suffix = _common_length(rest_old[::-1], rest_new[::-1])
        # Where the old tail began in the old text: the fixed part as it was before this update.
        tail_start = self._fixed_length - len(appended) + removed_head
        return OutputEdit(
            start=tail_start + prefix,
            end=tail_start + len(old_tail) - suffix,
            replacement=replacement[prefix : len(replacement) - suffix],
            removed_head=removed_head,
            trimmed_lines=trimmed_lines,
        )
