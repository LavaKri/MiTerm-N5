"""The commands that work on the text of the output: export, search, go to the cursor or emulator.

The dialogs and the caret are here; finding the word and saying it is
``presenters/output_search.py``. A search that finds something puts the focus in the output area
with the caret on the occurrence (a deliberate move, rule C of "Focus and caret" in
``specs/interface.md``); one that finds nothing leaves the focus and the caret where they were.
"""

import wx

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import ExportError
from n5terminal.core.screen.screen_elements import find_elements, initial_selection
from n5terminal.core.screen.text_search import cursor_is_on_line_text, line_at, neighbour_line
from n5terminal.core.session.output_export import export_output
from n5terminal.core.session.session_state import Mode
from n5terminal.i18n import _
from n5terminal.presenters.comfort_reading import ComfortReader
from n5terminal.presenters.line_reader import LineReader
from n5terminal.presenters.output_search import OutputSearch
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.output_area import OutputArea


class OutputCommands:
    """Export, Find, Find next, Find previous, Go to the terminal cursor and Read the line."""

    def __init__(
        self,
        presenter: SessionPresenter,
        feedback: Feedback,
        output: OutputArea,
        settings: Settings,
    ) -> None:
        self._presenter = presenter
        self._feedback = feedback
        self._output = output
        self._search = OutputSearch(presenter.say)
        self._reader = LineReader(presenter.say)
        self._comfort = ComfortReader(presenter.say, settings)

    def read_line(self) -> None:
        """Say the line of the caret with its formatting; the caret and the focus do not move."""
        text, caret = self._output.text, self._output.caret_index()
        on_text = cursor_is_on_line_text(text, caret, self._output.terminal_cursor_index())
        self._reader.read(line_at(text, caret), self._presenter.state.mode, cursor_on_text=on_text)

    def comfort_previous(self) -> None:
        """Move the caret to the line before and say it without its prompt."""
        self._comfort_move(forward=False)

    def comfort_next(self) -> None:
        """Move the caret to the line after and say it without its prompt."""
        self._comfort_move(forward=True)

    def _comfort_move(self, *, forward: bool) -> None:
        text = self._output.text
        index = neighbour_line(text, self._output.caret_index(), forward=forward)
        if index is None:
            self._presenter.say(Announce.NO_NEXT_LINE if forward else Announce.NO_PREVIOUS_LINE)
            return
        self._output.SetFocus()
        self._output.move_to(index)
        self._comfort.read(line_at(text, index), self._presenter.state.mode)

    def identify_activities(self) -> None:
        """List what is recognized in the last lines; the one picked gets the caret and focus."""
        found = find_elements(
            self._output.text,
            self._presenter.terminal_size.rows,
            selection_marks=self._presenter.state.mode is not Mode.PIPES,
            cursor_index=self._output.terminal_cursor_index(),
        )
        if not found:
            self._presenter.say(Announce.NO_ELEMENT_FOUND)
            return
        labels = [element.describe() for element in found]
        # The last one that is not an address first: it is usually the question that waits.
        choice = self._feedback.choose_with_copy(
            _("Identify activities"),
            _("Elements recognized"),
            labels,
            initial_selection(found),
            lambda index: self._copy(found[index].text),
        )
        if choice is not None:
            # Once the dialog is gone: Feedback puts the focus back where it was right after it.
            wx.CallAfter(self._go, found[choice].index)

    def _copy(self, text: str) -> None:
        """Put ``text`` (the address, or what is said of the element) in the clipboard.

        The clipboard belongs to the whole computer: another program may hold it, and then the
        user is told that nothing was copied.
        """
        copied = False
        if wx.TheClipboard.Open():
            try:
                copied = bool(wx.TheClipboard.SetData(wx.TextDataObject(text)))
            finally:
                wx.TheClipboard.Close()
        self._presenter.say(Announce.COPIED if copied else Announce.COPY_FAILED)

    def export(self) -> None:
        """Write the text of the output to a file chosen in a save dialog."""
        message = _(
            "Export the output. The file may contain secrets typed or shown in the session."
        )
        path = self._feedback.save_file(message, self._presenter.working_folder, _("output.txt"))
        if path is None:
            return
        try:
            export_output(path, self._output.text)
        except ExportError as error:
            self._feedback.show_error(
                _("The output could not be exported.\n{error}").format(error=error)
            )
            return

    def go_to_cursor(self) -> None:
        """Put the focus and the caret where the terminal cursor is, and read that line."""
        self._go_to(self._output.terminal_cursor_index(), Announce.MOVED_TO_CURSOR)

    def go_to_emulator_start(self) -> None:
        """Put the focus and the caret at the start of the emulator part, and read that line."""
        self._go_to(self._output.live_start_index(), Announce.MOVED_TO_EMULATOR_START)

    def go_to_emulator_end(self) -> None:
        """Put the focus and the caret at the end of the emulator part, and read that line."""
        self._go_to(self._output.live_end_index(), Announce.MOVED_TO_EMULATOR_END)

    def _go_to(self, index: int, announce: Announce) -> None:
        text = self._output.text
        self._output.SetFocus()
        self._output.move_to(index)
        self._presenter.say(announce, line=line_at(text, index) or _("blank"))

    def find(self) -> None:
        """Ask for a word and search it forward from the caret."""
        answer = self._feedback.ask_search(
            _("Find in the output"), self._search.term, self._search.upwards, self._search.regex
        )
        if answer is not None and answer[0]:
            # Once the dialog is gone: Feedback puts the focus back where it was right after it.
            wx.CallAfter(self._start, *answer)

    def find_next(self) -> None:
        """The next occurrence after the caret; Find when no word was searched yet."""
        if not self._search.term:
            self.find()
            return
        self._go(self._search.next(self._output.text, self._output.caret_index()))

    def find_previous(self) -> None:
        """The previous occurrence before the caret; Find when no word was searched yet."""
        if not self._search.term:
            self.find()
            return
        self._go(self._search.previous(self._output.text, self._output.caret_index()))

    def _start(self, term: str, upwards: bool = False, regex: bool = False) -> None:
        caret = self._output.caret_index()
        self._go(self._search.start(term, self._output.text, caret, upwards=upwards, regex=regex))

    def _go(self, index: int | None) -> None:
        if index is not None:
            self._output.SetFocus()
            self._output.move_to(index)
