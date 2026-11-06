"""The output area: a read-only native text control that a screen reader reads.

The text is kept by ``presenters/output_text.py``, which also finds the smallest change to make at
each update and where the caret goes, so the update is silent: output arriving never moves the
focus or the caret (rule C of "Focus and caret" in ``specs/interface.md``). A multi-line
control is used because the Tab key reaches it and a screen reader reads it; ``TE_RICH2`` lifts the
size limit of the plain control and counts a line break as one character.
"""

from collections.abc import Callable

import wx

from n5terminal.core.screen.screen_model import ScreenUpdate
from n5terminal.core.screen.titles import from_utf16, to_utf16
from n5terminal.i18n import _
from n5terminal.presenters.output_text import OutputEdit, OutputText
from n5terminal.ui.context_menu import popup_context_menu

# The keys 1 to 6 (main row and numeric pad) go to a title of that level, T to any title.
_LEVEL_KEYS = {ord(str(level)): level for level in range(1, 7)}
_LEVEL_KEYS.update({getattr(wx, f"WXK_NUMPAD{level}"): level for level in range(1, 7)})
_ANY_TITLE_KEY = ord("T")

TitleHandler = Callable[[int | None, bool], None]  # level (None: any), backwards


class OutputArea(wx.TextCtrl):
    """The text of the session. ``on_title`` is called for the keys that go from title to title;
    ``on_position`` with (line, total lines, column, width) whenever the caret may have moved."""

    def __init__(
        self,
        parent: wx.Window,
        limit: int,
        on_title: TitleHandler,
        on_position: Callable[[int, int, int, int], None],
        *,
        show_history: bool = True,
    ) -> None:
        super().__init__(
            parent, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, name=_("Output")
        )
        self._output = OutputText(limit, show_history=show_history)
        self._on_title = on_title
        self._on_position = on_position
        self.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.Bind(wx.EVT_KEY_UP, lambda event: self._after_move(event))
        self.Bind(wx.EVT_LEFT_UP, lambda event: self._after_move(event))
        self.Bind(wx.EVT_RIGHT_UP, self._on_right_up)
        self.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._context_menu: wx.Menu | None = None

    def set_context_menu(self, menu: wx.Menu) -> None:
        """The menu of the area (right click, Application key, Shift+F10)."""
        self._context_menu = menu

    def _on_right_up(self, event: wx.MouseEvent) -> None:
        """A read-only rich text control shows its own menu on a right click: take it over."""
        if self._context_menu is None:
            event.Skip()
            return
        self.PopupMenu(self._context_menu, event.GetPosition())

    def _show_menu_at_caret(self) -> None:
        """The menu from the keyboard (Application key, Shift+F10), at the text caret."""
        if self._context_menu is None:
            return
        position = self.PositionToCoords(self.GetInsertionPoint())
        self.PopupMenu(
            self._context_menu, position if position != wx.DefaultPosition else wx.Point(0, 0)
        )

    def _on_context_menu(self, event: wx.ContextMenuEvent) -> None:
        if self._context_menu is None:
            event.Skip()
            return
        popup_context_menu(self, self._context_menu, event)

    @property
    def text(self) -> str:
        """The text of the output, with ``\\n`` as line break."""
        return self._output.text

    def caret_index(self) -> int:
        """The caret as a string index of ``text``."""
        return from_utf16(self._output.text, self.GetInsertionPoint())

    def terminal_cursor_index(self) -> int:
        """The terminal cursor as a string index of ``text``."""
        return self._output.terminal_cursor_index()

    def live_start_index(self) -> int:
        """The start of the live part (the emulator) as a string index of ``text``."""
        return self._output.live_start_index()

    def focus_on_command(self, lines: int) -> None:
        """Put the focus in the area and the caret at the start of the command just written.

        ``lines`` is how many lines the command took (its title and what is under it); 0 when
        the command is not written (a terminal program): the caret goes to the live part.
        """
        self.SetFocus()
        self.move_to(self._output.fixed_line_start(lines) if lines else self.live_start_index())

    def live_end_index(self) -> int:
        """The end of the live part as a string index of ``text``."""
        return self._output.live_end_index()

    def move_to(self, index: int) -> None:
        """Put the caret at the string index ``index`` and say where it is."""
        self.SetInsertionPoint(to_utf16(self._output.text, index))
        self.ShowPosition(self.GetInsertionPoint())
        self.report_position()

    def set_limit(self, limit: int) -> None:
        self._output.set_limit(limit)

    @property
    def show_history(self) -> bool:
        return self._output.show_history

    def set_show_history(self, show_history: bool) -> None:
        """With history, a terminal keeps its fixed lines and hides its blank rows; else not."""
        old_text = self._output.text
        edit = self._output.set_show_history(show_history)
        if edit is not None:
            self._apply(edit, old_text)

    def show(self, update: ScreenUpdate) -> int:
        """Take an update of the screen model: the change is made without moving the caret.

        Returns how many of the oldest lines the limit removed.
        """
        old_text = self._output.text
        edit = self._output.apply(update)
        if edit is None:
            return 0
        self._apply(edit, old_text)
        return edit.trimmed_lines

    def clear_text(self) -> None:
        old_text = self._output.text
        edit = self._output.clear()
        if edit is not None:
            self._apply(edit, old_text)

    def report_position(self) -> None:
        """Tell the line and the column the caret is on, and how many lines and columns there are.

        The width is that of the terminal screen; with pipes there is none, so it is the length
        of the line.
        """
        _ok, column, row = self.PositionToXY(self.GetInsertionPoint())
        width = self._output.columns or len(self.GetLineText(row))
        self._on_position(row + 1, self.GetNumberOfLines(), column + 1, max(width, column + 1))

    # Inside ------------------------------------------------------------------------------------

    def _apply(self, edit: OutputEdit, old_text: str) -> None:
        caret = from_utf16(old_text, self.GetInsertionPoint())
        first, last = self.GetSelection()
        selection = (from_utf16(old_text, first), from_utf16(old_text, last))
        self.Freeze()
        try:
            self.Replace(
                to_utf16(old_text, edit.start), to_utf16(old_text, edit.end), edit.replacement
            )
            if edit.removed_head:
                replaced = old_text[: edit.start] + edit.replacement + old_text[edit.end :]
                self.Remove(0, to_utf16(replaced, edit.removed_head))
        finally:
            self.Thaw()
        new_text = self._output.text
        if selection[0] != selection[1]:
            self.SetSelection(
                to_utf16(new_text, self._output.caret_after(selection[0], edit)),
                to_utf16(new_text, self._output.caret_after(selection[1], edit)),
            )
        else:
            self.SetInsertionPoint(to_utf16(new_text, self._output.caret_after(caret, edit)))
        if not self.HasFocus():
            self.ShowPosition(self.GetLastPosition())  # follow the end, without moving the caret

    def _on_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        plain = not (event.ControlDown() or event.AltDown() or event.MetaDown())
        if code == wx.WXK_WINDOWS_MENU or (code == wx.WXK_F10 and event.ShiftDown() and plain):
            self._show_menu_at_caret()  # the control would show its own menu: ours replaces it
            return
        if plain and (code in _LEVEL_KEYS or code == _ANY_TITLE_KEY):
            self._on_title(_LEVEL_KEYS.get(code), event.ShiftDown())
            return
        wx.CallAfter(self.report_position)  # once the control has moved the caret
        event.Skip()

    def _after_move(self, event: wx.Event) -> None:
        wx.CallAfter(self.report_position)
        event.Skip()
