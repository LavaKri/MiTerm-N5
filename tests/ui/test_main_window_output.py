"""Export and search in the main window: the items, the file written, where the caret and the
focus go. The dialogs are replaced by answers; the logic is tested in ``tests/presenters``."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_clipboard import FakeClipboard
from fakes.fake_launcher import FakeLauncher
from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.announcements import ACTIVITY, Destination
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.command_shortcuts import COMMAND_OF_SHORTCUT
from n5terminal.core.session.session_state import CommandId
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui

OUTPUT = b"first\nError one\nfine\nerror two\n"


def pump() -> None:
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.Yield()


@pytest.fixture
def launcher() -> FakeLauncher:
    return FakeLauncher()


@pytest.fixture
def window(app: wx.App, launcher: FakeLauncher, tmp_path: Path) -> Iterator[MainWindow]:
    frame = MainWindow(Settings.load(None), launcher, tmp_path)
    frame.Show()
    pump()
    yield frame
    frame.Close(force=True)


def recording(window: MainWindow) -> RecordingMessageSink:
    """Collect what the window announces."""
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    return sink


def with_output(window: MainWindow, launcher: FakeLauncher) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(OUTPUT)
    window.presenter.tick()
    pump()
    window.command.focus_field()  # launching the program put the focus in the output area
    window.output.SetInsertionPoint(0)  # the caret follows the end of what arrives; go to the top
    pump()


def answer_search(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    term: str | None,
    upwards: bool = False,
    regex: bool = False,
) -> list[str]:
    """The Find box answers ``term`` (the direction, the kind); returns the texts it was opened
    with."""
    defaults: list[str] = []

    def ask_search(
        title: str, default: str, was_upwards: bool, was_regex: bool
    ) -> tuple[str, bool, bool] | None:
        defaults.append(default)
        return None if term is None else (term, upwards, regex)

    monkeypatch.setattr(window.feedback, "ask_search", ask_search)
    return defaults


def item_enabled(window: MainWindow, command: CommandId) -> bool:
    return all(item.IsEnabled() for item in window.menus.items[command])


# Menus -----------------------------------------------------------------------------------------


def test_export_and_search_wait_for_some_output(window: MainWindow, launcher: FakeLauncher) -> None:
    commands = (CommandId.EXPORT, CommandId.FIND, CommandId.FIND_NEXT, CommandId.FIND_PREVIOUS)
    assert not any(item_enabled(window, command) for command in commands)
    with_output(window, launcher)
    assert all(item_enabled(window, command) for command in commands)


def test_a_refused_search_says_why(window: MainWindow) -> None:
    sink = recording(window)
    window.actions.run(CommandId.FIND)
    assert sink.messages == ["The output is empty."]


# Export ----------------------------------------------------------------------------------------


def test_export_writes_the_output_and_says_nothing_the_file_dialog_was_enough(
    window: MainWindow, launcher: FakeLauncher, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    target = tmp_path / "saved.txt"
    monkeypatch.setattr(window.feedback, "save_file", lambda message, folder, name: target)
    sink = recording(window)
    window.actions.run(CommandId.EXPORT)
    text = target.read_text(encoding="utf-8").splitlines()
    assert [text[0], *text[2:4]] == ["# ping host", "first", "Error one"]
    assert sink.messages == []


def test_a_cancelled_export_writes_nothing(
    window: MainWindow, launcher: FakeLauncher, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    monkeypatch.setattr(window.feedback, "save_file", lambda message, folder, name: None)
    window.actions.run(CommandId.EXPORT)
    assert list(tmp_path.iterdir()) == []


def test_an_export_that_fails_is_reported(
    window: MainWindow, launcher: FakeLauncher, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    shown: list[str] = []
    monkeypatch.setattr(
        window.feedback, "save_file", lambda message, folder, name: tmp_path / "no" / "x.txt"
    )
    monkeypatch.setattr(window.feedback, "show_error", shown.append)
    window.actions.run(CommandId.EXPORT)
    assert len(shown) == 1
    assert shown[0].startswith("The output could not be exported.")


# Search ----------------------------------------------------------------------------------------


def test_find_puts_the_focus_and_the_caret_on_the_occurrence(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    answer_search(window, monkeypatch, "error")
    assert wx.Window.FindFocus() is window.command.field
    window.actions.run(CommandId.FIND)
    pump()
    assert wx.Window.FindFocus() is window.output
    assert window.output.caret_index() == window.output.text.index("Error one")
    assert window.GetStatusBar().GetStatusText(0) == "Line 4 of 7"


def test_find_next_and_previous_follow_the_word(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    answer_search(window, monkeypatch, "error")
    window.actions.run(CommandId.FIND)
    pump()
    window.actions.run(CommandId.FIND_NEXT)
    assert window.output.caret_index() == window.output.text.index("error two")
    window.actions.run(CommandId.FIND_PREVIOUS)
    assert window.output.caret_index() == window.output.text.index("Error one")


def test_find_next_without_a_word_asks_for_one(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    defaults = answer_search(window, monkeypatch, "fine")
    window.actions.run(CommandId.FIND_NEXT)
    pump()
    assert defaults == [""]
    assert window.output.caret_index() == window.output.text.index("fine")
    window.actions.run(CommandId.FIND)
    assert defaults == ["", "fine"]  # the dialog offers the last word


def test_a_search_without_result_leaves_the_focus_and_the_caret(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    answer_search(window, monkeypatch, "absent")
    window.actions.run(CommandId.FIND)
    pump()
    assert wx.Window.FindFocus() is window.command.field
    assert window.output.caret_index() == 0
    assert sink.messages == ['No next occurrence of "absent".']


def test_a_cancelled_search_does_nothing(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    answer_search(window, monkeypatch, None)
    window.actions.run(CommandId.FIND)
    pump()
    assert wx.Window.FindFocus() is window.command.field


def test_from_the_end_find_previous_reaches_the_last_occurrence(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    window.output.SetInsertionPoint(window.output.GetLastPosition())
    answer_search(window, monkeypatch, "error")
    window.actions.run(CommandId.FIND)
    pump()
    assert wx.Window.FindFocus() is window.command.field  # nothing after the caret
    window.actions.run(CommandId.FIND_PREVIOUS)
    assert wx.Window.FindFocus() is window.output
    assert window.output.caret_index() == window.output.text.index("error two")


# The terminal cursor ---------------------------------------------------------------------------


def test_go_to_the_cursor_puts_the_focus_and_the_caret_on_it(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    with_output(window, launcher)
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    window.actions.run(CommandId.GO_TO_CURSOR)
    assert wx.Window.FindFocus() is window.output
    assert window.output.caret_index() == len(window.output.text)  # end of the last line
    assert sink.messages == ["Terminal cursor: blank"]


def test_the_ends_of_the_emulator_part_are_the_ends_of_the_live_line(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(b"done\nunfinished")
    window.presenter.tick()
    pump()
    launcher.transport.exit(0)
    window.presenter.tick()
    pump()  # no program runs: the live part of the last output can be reached
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    window.actions.run(CommandId.GO_TO_EMULATOR_START)
    assert window.output.caret_index() == window.output.text.index("unfinished")
    window.actions.run(CommandId.GO_TO_EMULATOR_END)
    assert window.output.caret_index() == len(window.output.text)
    assert sink.messages == ["Start of the emulator: unfinished", "End of the emulator: unfinished"]


def test_the_emulator_part_is_refused_for_a_program_with_pipes(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    with_output(window, launcher)
    sink = recording(window)
    window.actions.run(CommandId.GO_TO_EMULATOR_START)
    assert sink.messages == ["Only for programs that use a terminal."]
    assert not item_enabled(window, CommandId.GO_TO_EMULATOR_END)


def test_the_shortcuts_of_the_emulator_part_stand_for_their_commands() -> None:
    assert COMMAND_OF_SHORTCUT["display.emulator_start"] is CommandId.GO_TO_EMULATOR_START
    assert COMMAND_OF_SHORTCUT["display.emulator_end"] is CommandId.GO_TO_EMULATOR_END


def test_go_to_the_cursor_waits_for_some_output(window: MainWindow) -> None:
    assert not item_enabled(window, CommandId.GO_TO_CURSOR)
    sink = recording(window)
    window.actions.run(CommandId.GO_TO_CURSOR)
    assert sink.messages == ["The output is empty."]


def test_read_the_line_says_the_line_of_the_caret_and_moves_nothing(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    with_output(window, launcher)
    window.output.SetInsertionPoint(window.output.text.index("Error one"))
    caret = window.output.caret_index()
    sink = recording(window)
    window.actions.run(CommandId.READ_LINE)
    assert sink.messages == ["Error one"]
    assert window.output.caret_index() == caret
    assert wx.Window.FindFocus() is window.command.field


def test_read_the_line_waits_for_some_output(window: MainWindow) -> None:
    assert not item_enabled(window, CommandId.READ_LINE)
    sink = recording(window)
    window.actions.run(CommandId.READ_LINE)
    assert sink.messages == ["The output is empty."]


def test_the_shortcut_of_the_formatted_line_stands_for_its_command() -> None:
    assert COMMAND_OF_SHORTCUT["activity.read_line"] is CommandId.READ_LINE


def test_identify_lists_the_elements_and_goes_to_the_one_picked(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(b"Download 40%\nContinue? [Y/n]\n")
    window.presenter.tick()
    pump()
    window.command.focus_field()
    asked: list[tuple[list[str], int]] = []

    def choose(
        title: str, prompt: str, labels: list[str], selected: int, copy: object
    ) -> int | None:
        asked.append((labels, selected))
        return 0

    monkeypatch.setattr(window.feedback, "choose_with_copy", choose)
    window.actions.run(CommandId.IDENTIFY_ACTIVITIES)
    pump()
    labels, selected = asked[0]
    assert labels[0].startswith("Progress, Download, 40 %, line ")
    assert labels[1].startswith("Question: Continue? Default answer: yes, line ")
    assert selected == 1  # the last one, usually the question that waits
    assert wx.Window.FindFocus() is window.output
    assert window.output.text[window.output.caret_index() :].startswith("Download 40%")


def test_identify_says_when_nothing_is_recognized(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    sink = recording(window)
    opened: list[str] = []
    monkeypatch.setattr(window.feedback, "choose_with_copy", lambda *args: opened.append("opened"))
    window.actions.run(CommandId.IDENTIFY_ACTIVITIES)
    assert sink.messages == ["No element recognized."]
    assert opened == []


def test_identify_waits_for_some_output(window: MainWindow) -> None:
    assert not item_enabled(window, CommandId.IDENTIFY_ACTIVITIES)
    assert COMMAND_OF_SHORTCUT["activity.identify"] is CommandId.IDENTIFY_ACTIVITIES


def test_signal_activities_switches_the_activity_off_and_back_on(window: MainWindow) -> None:
    sink = recording(window)
    item = window.menus.toggles[CommandId.SIGNAL_ACTIVITIES]
    assert item.IsChecked()
    window.actions.run(CommandId.SIGNAL_ACTIVITIES)
    assert not item.IsChecked()
    assert window.feedback.announcements.category_destination(ACTIVITY) is Destination.NONE
    window.actions.run(CommandId.SIGNAL_ACTIVITIES)
    assert item.IsChecked()
    assert window.feedback.announcements.category_destination(ACTIVITY) is (
        Destination.ELEMENT_OR_BEEP
    )
    assert sink.messages == ["Activity not signaled.", "Activity signaled."]


def test_the_shortcut_of_the_activity_stands_for_its_command() -> None:
    assert COMMAND_OF_SHORTCUT["activity.signal"] is CommandId.SIGNAL_ACTIVITIES


def test_identify_lists_the_addresses_and_copies_the_one_selected(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(
        b"See https://example.org/help or mail me@example.org\nProceed? [Y/n]\n"
    )
    window.presenter.tick()
    pump()
    sink = recording(window)
    clipboard = FakeClipboard()  # never the clipboard of the computer
    monkeypatch.setattr(wx, "TheClipboard", clipboard)
    asked: list[tuple[list[str], int]] = []

    def choose(
        title: str, prompt: str, labels: list[str], selected: int, copy: Callable[[int], None]
    ) -> int | None:
        asked.append((labels, selected))
        copy(0)  # the button, on the first line
        copy(1)
        return 0

    monkeypatch.setattr(window.feedback, "choose_with_copy", choose)
    window.actions.run(CommandId.IDENTIFY_ACTIVITIES)
    pump()
    labels, selected = asked[0]
    assert labels[:2] == ["https://example.org/help", "me@example.org"]  # only the address
    assert labels[2].startswith("Question: Proceed?")
    assert selected == 2  # the question that waits, not the last address above it
    assert sink.messages.count("Copied to the clipboard.") == 2
    assert clipboard.copied == ["https://example.org/help", "me@example.org"]  # in this order
    assert not clipboard.opened  # closed again after each copy
    assert window.output.text[window.output.caret_index() :].startswith("https://example.org/help")


@pytest.mark.parametrize(
    "trouble", [{"available": False}, {"accepts": False}], ids=["busy", "refuses the data"]
)
def test_a_copy_that_fails_is_announced_and_leaves_nothing_open(
    window: MainWindow,
    launcher: FakeLauncher,
    monkeypatch: pytest.MonkeyPatch,
    trouble: dict[str, bool],
) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(b"See https://example.org/help\n")
    window.presenter.tick()
    pump()
    sink = recording(window)
    clipboard = FakeClipboard(**trouble)
    monkeypatch.setattr(wx, "TheClipboard", clipboard)

    def choose(
        title: str, prompt: str, labels: list[str], selected: int, copy: Callable[[int], None]
    ) -> int | None:
        copy(0)
        return None

    monkeypatch.setattr(window.feedback, "choose_with_copy", choose)
    window.actions.run(CommandId.IDENTIFY_ACTIVITIES)
    pump()
    assert sink.messages == ["Nothing copied: the clipboard is not available."]
    assert clipboard.copied == []
    assert not clipboard.opened


# Comfortable reading -----------------------------------------------------------------------------


def prompt_output(window: MainWindow, launcher: FakeLauncher) -> None:
    window.presenter.submit("ping host")
    launcher.transport.receive(
        b"C:\\Users\\x>dir\na file\nPS C:\\Users\\x> git status\nOn branch main\n"
    )
    window.presenter.tick()
    pump()
    window.output.SetInsertionPoint(0)
    pump()


def test_the_next_line_is_said_without_its_prompt_and_the_caret_goes_there(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    prompt_output(window, launcher)
    text = window.output.text
    start = text.index("C:\\Users\\x>dir")
    window.output.SetInsertionPoint(start)
    sink = recording(window)
    window.actions.run(CommandId.COMFORT_NEXT)
    assert window.output.caret_index() == text.index("a file")
    assert sink.messages == ["a file"]
    window.actions.run(CommandId.COMFORT_NEXT)
    assert sink.messages[-1] == "Command git status"
    assert wx.Window.FindFocus() is window.output


def test_the_previous_line_is_said_without_its_prompt(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    prompt_output(window, launcher)
    text = window.output.text
    window.output.SetInsertionPoint(text.index("a file"))
    sink = recording(window)
    window.actions.run(CommandId.COMFORT_PREVIOUS)
    assert window.output.caret_index() == text.index("C:\\Users\\x>dir")
    assert sink.messages == ["Command dir"]


def test_at_the_first_and_the_last_line_nothing_moves_and_it_is_said(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    prompt_output(window, launcher)
    text = window.output.text
    sink = recording(window)
    window.output.SetInsertionPoint(0)
    window.actions.run(CommandId.COMFORT_PREVIOUS)
    assert sink.messages[-1] == "No previous line."
    window.output.SetInsertionPoint(len(text))  # the empty line after the last break
    caret = window.output.caret_index()
    window.actions.run(CommandId.COMFORT_NEXT)
    assert sink.messages[-1] == "No next line."
    assert window.output.caret_index() == caret


def test_the_arrows_still_read_the_whole_line(window: MainWindow, launcher: FakeLauncher) -> None:
    prompt_output(window, launcher)
    assert r"PS C:\Users\x> git status" in window.output.text  # nothing was removed from the text


def test_comfortable_reading_waits_for_some_output(window: MainWindow) -> None:
    assert not item_enabled(window, CommandId.COMFORT_NEXT)
    sink = recording(window)
    window.actions.run(CommandId.COMFORT_NEXT)
    assert sink.messages == ["The output is empty."]


def test_the_shortcuts_stand_for_their_commands_and_are_ctrl_alt_up_and_down() -> None:
    assert COMMAND_OF_SHORTCUT["output.comfort_previous"] is CommandId.COMFORT_PREVIOUS
    assert COMMAND_OF_SHORTCUT["output.comfort_next"] is CommandId.COMFORT_NEXT


def test_the_dialog_of_the_patterns_keeps_the_list_and_the_formatting_in_the_settings(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    from n5terminal.ui.prompt_patterns_dialog import PromptPatternsDialog  # noqa: PLC0415

    def accept(dialog: PromptPatternsDialog) -> int:
        dialog._editor.add("mine", r"\$ ")
        dialog._editor.formatting = False
        return int(wx.ID_OK)

    monkeypatch.setattr(PromptPatternsDialog, "ShowModal", accept)
    window.actions.run(CommandId.PROMPT_PATTERNS)
    assert window._settings.patterns()[-1].name == "mine"
    assert window._settings.comfort_formatting is False


# The box of Find: the direction -------------------------------------------------------------------


def test_the_box_of_find_can_search_upwards_from_the_caret(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    window.output.SetInsertionPoint(window.output.text.index("error two"))
    answer_search(window, monkeypatch, "error", upwards=True)
    window.actions.run(CommandId.FIND)
    pump()
    assert window.output.caret_index() == window.output.text.index("Error one")


def test_the_direction_of_the_box_does_not_change_find_next_and_find_previous(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    answer_search(window, monkeypatch, "error", upwards=True)
    window.actions.run(CommandId.FIND)  # nothing before the first line: no occurrence upwards
    pump()
    assert window.output.caret_index() == 0
    window.actions.run(CommandId.FIND_NEXT)
    pump()
    assert window.output.caret_index() == window.output.text.index("Error one")


def test_the_box_offers_the_direction_it_was_last_used_with(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    offered: list[tuple[bool, bool]] = []

    def ask_search(
        title: str, default: str, upwards: bool, regex: bool
    ) -> tuple[str, bool, bool] | None:
        offered.append((upwards, regex))
        return ("error", True, True)

    monkeypatch.setattr(window.feedback, "ask_search", ask_search)
    window.actions.run(CommandId.FIND)
    pump()
    window.actions.run(CommandId.FIND)
    assert offered == [(False, False), (True, True)]


def test_the_box_of_find_can_search_a_regular_expression_and_f3_keeps_its_kind(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_output(window, launcher)
    answer_search(window, monkeypatch, r"err\w+ (one|two)", regex=True)
    window.actions.run(CommandId.FIND)
    pump()
    assert window.output.caret_index() == window.output.text.index("Error one")
    window.actions.run(CommandId.FIND_NEXT)
    pump()
    assert window.output.caret_index() == window.output.text.index("error two")
