"""What the main window tells the user: the status bar, the announcements and the dialogs.

Every dialog of the application is shown through :meth:`Feedback.modal`, which puts the focus back
where it was when the dialog closes (rule A of "Focus and caret" in
``specs/interface.md``).
"""

import logging
from collections.abc import Callable
from pathlib import Path

import wx

from n5terminal.core.config.announcements import AnnouncementCenter, Beeper, NullMessageSink
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import ScreenReaderOutputError, SettingsError
from n5terminal.i18n import _
from n5terminal.ui.elements_dialog import ElementsDialog
from n5terminal.ui.find_dialog import FindDialog
from n5terminal.ui.message_sinks import create_sink

logger = logging.getLogger(__name__)

_LINE_FIELD = 0
_STATE_FIELD = 1
_COLUMN_FIELD = 2
STATUS_TEXT_LIMIT = 200  # characters: a screen reader reads a field in one go


def shorten(text: str, limit: int = STATUS_TEXT_LIMIT) -> str:
    """``text`` on one line, cut with an ellipsis when it is longer than ``limit``."""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"


class Feedback:
    """Says things to the user through ``frame``: its status bar, the screen reader, dialogs.

    ``is_closing`` tells whether the window is closing (the focus is then left alone).
    """

    def __init__(
        self,
        frame: wx.Frame,
        settings: Settings,
        is_closing: Callable[[], bool],
        beeper: Beeper | None = None,
    ) -> None:
        self._frame = frame
        self._settings = settings
        self._is_closing = is_closing
        frame.CreateStatusBar(3)
        frame.SetStatusWidths([-2, -3, -2])
        self.announcements = AnnouncementCenter(
            destination_of=settings.destination_for,
            on_error=self._on_screen_reader_error,
            show_dialog=self.show_info,
            beeper=beeper,
        )

    def apply_screen_reader_output(self, output_id: str) -> None:
        """Send the announcements through the output ``output_id`` from now on.

        The window must already hold its panel (the hidden window of the output goes in it). If
        the output cannot be made the user is told and the announcements go nowhere.
        """
        center = self.announcements
        center.message_sink.close()
        try:
            center.message_sink = create_sink(output_id, self._frame)
        except ScreenReaderOutputError as error:
            center.message_sink = NullMessageSink()
            self._on_screen_reader_error(error)

    def close(self) -> None:
        """Release what the announcements use, before the window is destroyed."""
        self.announcements.message_sink.close()

    # Status bar --------------------------------------------------------------------------------

    def set_state(self, text: str) -> None:
        """Second field: the state of the session."""
        self._set_field(text, _STATE_FIELD)

    def set_position(self, line: int, total: int, column: int, width: int) -> None:
        """First and third fields: the line and the column the caret is on in the output."""
        line_text = _("Line {number} of {total}").format(number=line, total=total) if total else ""
        column_text = _("Column {number} of {total}").format(number=column, total=width)
        self._set_field(line_text, _LINE_FIELD)
        self._set_field(column_text if total else "", _COLUMN_FIELD)

    def set_title(self, text: str) -> None:
        """The title of the window."""
        self._frame.SetTitle(text)

    def _set_field(self, text: str, field: int) -> None:
        self._frame.SetStatusText(shorten(text), field)

    def _on_screen_reader_error(self, error: ScreenReaderOutputError) -> None:
        self.show_error(_("The screen reader output cannot be used.\n{error}").format(error=error))

    def save_settings(self) -> None:
        """Write the settings; if that fails the user is told, and the application goes on."""
        try:
            self._settings.save()
        except SettingsError as error:
            self.show_error(_("The settings could not be saved.\n{error}").format(error=error))

    # Dialogs -----------------------------------------------------------------------------------

    def modal(self, dialog: wx.Dialog) -> int:
        """Show ``dialog``; when it closes the focus is back where it was."""
        focused = wx.Window.FindFocus()
        name = type(dialog).__name__
        logger.debug("Dialog opened: %s", name)
        try:
            code = int(dialog.ShowModal())
            logger.debug("Dialog closed: %s (%s)", name, code)
            return code
        finally:
            wx.CallAfter(self._restore_focus, focused)  # once the dialog is destroyed

    def _restore_focus(self, focused: wx.Window | None) -> None:
        """Put the focus back on ``focused`` unless it was deliberately moved inside the window."""
        frame = self._frame
        if self._is_closing() or not frame or not focused:
            return
        if any(isinstance(w, wx.Dialog) and w.IsModal() for w in wx.GetTopLevelWindows()):
            return  # another box opened since: the focus is its own (setting it elsewhere aborts)
        current = wx.Window.FindFocus()
        if current is None or not frame.IsDescendant(current):
            focused.SetFocus()

    def message_box(self, message: str, caption: str, icon: int) -> None:
        """A message with an OK button; the focus comes back where it was."""
        with wx.MessageDialog(self._frame, message, caption, wx.OK | icon) as dialog:
            self.modal(dialog)

    def show_error(self, message: str) -> None:
        logger.error("Error shown to the user: %s", message)
        self.message_box(message, _("Error"), wx.ICON_ERROR)

    def show_info(self, message: str) -> None:
        self.message_box(message, _("Information"), wx.ICON_INFORMATION)

    def confirm(self, title: str, message: str) -> bool:
        """Ask a Yes / No question, No by default; True for Yes."""
        style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        with wx.MessageDialog(self._frame, message, title, style) as dialog:
            return bool(self.modal(dialog) == wx.ID_YES)

    def choose(self, title: str, prompt: str, labels: list[str], selected: int = 0) -> int | None:
        """Ask the user to pick one of ``labels``, ``selected`` first; its index, ``None`` if
        cancelled."""
        with wx.SingleChoiceDialog(self._frame, prompt, title, labels) as dialog:
            dialog.SetSelection(selected)
            if self.modal(dialog) != wx.ID_OK:
                return None
            return int(dialog.GetSelection())

    def choose_with_copy(
        self,
        title: str,
        prompt: str,
        labels: list[str],
        selected: int,
        copy: Callable[[int], None],
    ) -> int | None:
        """Like :meth:`choose`, with a button that calls ``copy(index)`` for the line selected."""
        with ElementsDialog(self._frame, title, prompt, labels, selected, copy) as dialog:
            if self.modal(dialog) != wx.ID_OK:
                return None
            return int(dialog.selection())

    def choose_folder(self, start: Path) -> Path | None:
        """A native folder dialog opened on ``start``; ``None`` if cancelled."""
        with wx.DirDialog(
            self._frame, _("Working folder"), str(start), wx.DD_DIR_MUST_EXIST
        ) as dialog:
            if self.modal(dialog) != wx.ID_OK:
                return None
            return Path(dialog.GetPath())

    def save_file(self, message: str, folder: Path, name: str) -> Path | None:
        """A native save dialog opened on ``folder``, asking before it replaces a file.

        ``message`` is the title of the dialog, which a screen reader reads when it opens. ``None``
        if cancelled.
        """
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        files = "{text}|*.txt|{every}|*.*".format(
            text=_("Text files (*.txt)"), every=_("All files (*.*)")
        )
        with wx.FileDialog(self._frame, message, str(folder), name, files, style) as dialog:
            if self.modal(dialog) != wx.ID_OK:
                return None
            return Path(dialog.GetPath())

    def ask_search(
        self, title: str, term: str, upwards: bool, regex: bool
    ) -> tuple[str, bool, bool] | None:
        """The box of Find: the text to search (``term`` offered, selected), whether to search
        upwards and whether the text is a regular expression (both offered as they were);
        ``None`` if cancelled."""
        with FindDialog(self._frame, title, term, upwards, regex) as dialog:
            if self.modal(dialog) != wx.ID_OK:
                return None
            return dialog.term(), dialog.search_upwards(), dialog.use_regex()

    def ask_text(self, title: str, prompt: str, default: str = "") -> str | None:
        """A dialog with a one-line field (focused, ``default`` selected); ``None`` if cancelled."""
        with wx.TextEntryDialog(self._frame, prompt, title, default) as dialog:
            if self.modal(dialog) != wx.ID_OK:
                return None
            return str(dialog.GetValue())

    def show_text(self, title: str, text: str) -> None:
        """A dialog with a read-only text (one line per item), closed with Escape or OK."""
        with wx.Dialog(
            self._frame, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        ) as dialog:
            field = wx.TextCtrl(
                dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, name=title
            )
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(field, 1, wx.EXPAND | wx.ALL, 8)
            sizer.Add(dialog.CreateStdDialogButtonSizer(wx.OK), 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizerAndFit(sizer)
            dialog.SetSize(wx.Size(560, 420))
            field.SetFocus()
            self.modal(dialog)
