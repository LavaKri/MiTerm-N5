"""Light checks of the main window: names, focus, Tab order, greyed items, silent updates.

The logic is tested without a window (``tests/presenters``); here only what a window can get wrong.
"""

import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import CONFIGURABLE_COMMANDS, display_shortcut
from n5terminal.core.session.session_state import CommandId, Interpreter, LaunchMode, Phase
from n5terminal.i18n import _ as translate
from n5terminal.i18n import install
from n5terminal.presenters.session_view import InputMode
from n5terminal.ui.main_window import MainWindow
from n5terminal.ui.multiline_dialog import MultilineDialog
from n5terminal.ui.wx_locale import init_wx_locale

pytestmark = pytest.mark.ui


def from_line(window: MainWindow) -> str:
    """The line under the title of a launched command."""
    return f"From {window.presenter.working_folder}{os.sep}"


def pump() -> None:
    """Let the window handle what is waiting (the posted events, the timer)."""
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


def item_enabled(window: MainWindow, command: CommandId) -> bool:
    return all(item.IsEnabled() for item in window.menus.items[command])


def run_and_receive(window: MainWindow, launcher: FakeLauncher, data: bytes) -> None:
    if window.presenter.state.phase is Phase.IDLE:
        window.presenter.submit("ping host")
    launcher.transport.receive(data)
    window.presenter.tick()
    pump()


# Names and focus -------------------------------------------------------------------------------


def test_the_initial_focus_is_the_command_field(window: MainWindow) -> None:
    assert wx.Window.FindFocus() is window.command.field


def test_every_control_has_a_name(window: MainWindow) -> None:
    assert window.command.field.GetName() == "Command"
    assert window.command.button.GetLabel() == "Send"
    assert window.output.GetName() == "Output"


def test_the_tab_order_is_the_command_field_the_hide_box_the_button_then_the_output(
    window: MainWindow,
) -> None:
    window.presenter.submit("ping host")  # the box is greyed (out of the Tab order) at rest
    pump()
    names: list[str] = []
    for child in window.output.GetParent().GetChildren():
        if child is window.command:
            parts = {
                window.command.field: "field",
                window.command.hide_box: "hide box",
                window.command.button: "button",
            }
            names.extend(parts[part] for part in child.GetChildren() if part in parts)
        elif child is window.output:
            names.append("output")
    assert names == ["field", "hide box", "button", "output"]


def test_the_field_is_named_after_what_it_is_for(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    pump()
    assert window.command.field.GetName() == "Message"
    launcher.transport.exit(0)
    pump()
    assert window.command.field.GetName() == "Command"


def test_the_output_is_read_only_and_reached_by_tab(window: MainWindow) -> None:
    assert not window.output.IsEditable()
    assert window.output.AcceptsFocusFromKeyboard()


# Menus -----------------------------------------------------------------------------------------


def test_open_logs_shows_the_log_folder_or_says_there_is_none(
    app: wx.App, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[object] = []
    monkeypatch.setattr("os.startfile", opened.append, raising=False)
    logs = tmp_path / "logs"
    frame = MainWindow(Settings.load(None), FakeLauncher(), tmp_path, AppContext(log_folder=logs))
    shown: list[str] = []
    monkeypatch.setattr(frame.feedback, "show_info", shown.append)
    try:
        assert all(item.IsEnabled() for item in frame.menus.items[CommandId.OPEN_LOGS])
        frame.actions.run(CommandId.OPEN_LOGS)
        assert opened == []
        assert shown == ["There is no log yet."]
        logs.mkdir()
        frame.actions.run(CommandId.OPEN_LOGS)
        assert opened == [logs]
    finally:
        frame.Close(force=True)


def assert_access_keys_are_unique(window: MainWindow) -> None:
    bar = window.GetMenuBar()
    assert bar.GetMenuCount() == 7
    titles = [title for _menu, title in bar.GetMenus()]
    keys = [title[title.index("&") + 1].lower() for title in titles]
    assert len(keys) == len(set(keys)), titles
    for menu, _title in bar.GetMenus():
        labels = [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]
        keys = [label[label.index("&") + 1].lower() for label in labels if "&" in label]
        assert len(keys) == len(set(keys)), labels


def test_access_keys_are_unique_inside_each_menu(window: MainWindow) -> None:
    assert_access_keys_are_unique(window)


def test_access_keys_are_unique_in_french_too(app: wx.App, tmp_path: Path) -> None:
    install("fr")
    frame = MainWindow(Settings.load(None), FakeLauncher(), tmp_path)
    try:
        assert_access_keys_are_unique(frame)
        assert frame.command.field.GetName() == "Commande"
        assert frame.command.button.GetLabel() == "Envoyer"
    finally:
        frame.Close(force=True)
        install("en")


def _accelerated_items(frame: MainWindow) -> list[tuple[wx.MenuItem, str]]:
    """Every item that has a shortcut, with the shortcut chosen (English spelling)."""
    return [
        (item, frame._settings.shortcut_for(frame.menus._commands[shortcut_id]))
        for item, _text, shortcut_id in frame.menus._with_shortcut
        if shortcut_id is not None
        and frame._settings.shortcut_for(frame.menus._commands[shortcut_id])
    ]


def _check_accelerators(frame: MainWindow, language: str) -> None:
    items = _accelerated_items(frame)
    assert len(items) >= 18  # the commands of the menus, and the keys sent that have one
    for item, shortcut in items:
        expected = wx.AcceleratorEntry()
        assert expected.FromString("\t" + shortcut), shortcut
        accel = item.GetAccel()
        assert accel is not None, shortcut
        assert (accel.GetFlags(), accel.GetKeyCode()) == (
            expected.GetFlags(),
            expected.GetKeyCode(),
        )
        # what the menu shows is how the application says the keys
        shown = display_shortcut(shortcut, translate) if language == "fr" else shortcut
        assert accel.ToString() == shown, shortcut


@pytest.mark.parametrize("language", ["fr", "en"])
def test_every_shortcut_of_a_menu_is_its_accelerator_with_the_names_of_the_language(
    app: wx.App, tmp_path: Path, language: str
) -> None:
    """Before the catalog of wx, "Maj+Entrée" was read as the key Enter alone."""
    install(language)
    locale = init_wx_locale(language)  # must stay referenced while the window exists
    frame = MainWindow(Settings.load(None), FakeLauncher(), tmp_path)
    try:
        _check_accelerators(frame, language)
        if language == "fr":
            start = frame.menus.items[CommandId.GO_TO_EMULATOR_START][0]
            assert start.GetItemLabel().endswith("\tAlt+Début")  # not "Alt+Dossier personnel"
    finally:
        frame.Close(force=True)
        install("en")
        del locale


def test_the_stop_key_works_for_ctrl_break_too(window: MainWindow) -> None:
    """Windows sends Ctrl+Pause as Ctrl+Break: the table of the window has that key for the item."""
    stop = window.menus.items[CommandId.STOP][0]
    assert (wx.ACCEL_CTRL, wx.WXK_CANCEL, stop.GetId()) in window.menus.break_accelerators()


def test_items_are_greyed_never_hidden(window: MainWindow) -> None:
    assert not item_enabled(window, CommandId.STOP)
    assert item_enabled(window, CommandId.NEW_SESSION)
    window.presenter.submit("ping host")
    pump()
    assert item_enabled(window, CommandId.STOP)
    assert not item_enabled(window, CommandId.CHOOSE_FOLDER)
    assert not item_enabled(window, CommandId.SET_MODE)


def test_the_mode_and_the_interpreter_are_checked(window: MainWindow) -> None:
    assert window.menus.choices["mode"][LaunchMode.CLI].IsChecked()
    window.actions.set_mode(LaunchMode.TUI)
    assert window.menus.choices["mode"][LaunchMode.TUI].IsChecked()
    window.actions.set_interpreter(Interpreter.CMD)
    assert window.menus.choices["interpreter"][Interpreter.CMD].IsChecked()
    assert window.menus.choices["mode"][LaunchMode.TUI].IsChecked()  # a shell is always TUI


def test_a_refused_command_says_why(window: MainWindow) -> None:
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    window.actions.run(CommandId.STOP)
    assert sink.messages == ["No program is running."]


# The output ------------------------------------------------------------------------------------


def test_the_output_shows_the_command_and_what_the_program_wrote(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    run_and_receive(window, launcher, b"reply\nlast")
    expected = f"# ping host\n{from_line(window)}\nreply\nlast"
    assert window.output.GetValue() == expected
    assert window.output.text == expected


def test_new_output_does_not_move_the_caret(window: MainWindow, launcher: FakeLauncher) -> None:
    run_and_receive(window, launcher, b"one\ntwo\n")
    window.output.SetFocus()
    window.output.SetInsertionPoint(3)
    run_and_receive(window, launcher, b"three\nfour\n")
    assert window.output.GetInsertionPoint() == 3
    assert window.output.GetValue().startswith(
        f"# ping host\n{from_line(window)}\none\ntwo\nthree\nfour\n"
    )


def test_a_caret_in_the_live_line_keeps_its_column(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    run_and_receive(window, launcher, b"done\nprogress 10%")
    window.output.SetFocus()
    window.output.SetInsertionPoint(window.output.GetValue().index("10%") + 1)
    run_and_receive(window, launcher, b"\rprogress 20%")
    assert window.output.GetValue().endswith("progress 20%")
    assert window.output.GetInsertionPoint() == window.output.GetValue().index("20%") + 1


def test_new_output_does_not_take_the_focus(window: MainWindow, launcher: FakeLauncher) -> None:
    run_and_receive(window, launcher, b"text\n")
    window.command.focus_field()  # launching the program put the focus in the output area
    pump()
    run_and_receive(window, launcher, b"more\n")
    assert wx.Window.FindFocus() is window.command.field


def test_the_title_keys_go_from_command_to_command(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    run_and_receive(window, launcher, b"reply\n")
    launcher.transport.exit(0)
    pump()
    window.presenter.submit("git log")
    run_and_receive(window, launcher, b"commit abc\n")
    window.output.SetInsertionPoint(0)
    window.actions.go_to_title(1, False)
    assert window.output.GetInsertionPoint() == window.output.GetValue().index("# git log")
    window.actions.go_to_title(1, True)
    assert window.output.GetInsertionPoint() == 0
    window.actions.go_to_title(1, True)  # nothing before the first
    assert window.output.GetInsertionPoint() == 0


def test_the_position_is_shown_in_the_status_bar(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    run_and_receive(window, launcher, b"one\ntwo\n")
    window.output.SetFocus()
    window.output.SetInsertionPoint(0)
    window.output.report_position()
    bar = window.GetStatusBar()
    assert bar.GetStatusText(0) == "Line 1 of 5"
    assert bar.GetStatusText(1) == "Running: ping"
    assert bar.GetStatusText(2).startswith("Column 1 of ")


def test_a_new_shortcut_reaches_the_menu_and_the_keys(window: MainWindow) -> None:
    stop = next(c for c in CONFIGURABLE_COMMANDS if c.id == "program.stop")
    window._settings.set_shortcut(stop, "Ctrl+K")
    window.refresh_shortcuts()
    labels = [item.GetItemLabel() for item in window.menus.items[CommandId.STOP]]
    assert any(label.endswith("Ctrl+K") for label in labels)
    assert not any("Ctrl+Pause" in label for label in labels)
    assert window._shortcuts.get("Ctrl+K") is CommandId.STOP
    assert "Ctrl+Pause" not in window._shortcuts


def test_the_choices_of_the_menus_and_the_connection_have_shortcuts_by_default(
    window: MainWindow,
) -> None:
    expected = {
        "F6": CommandId.CONNECT,
        "F7": CommandId.DISCONNECT,
        "Shift+F5": CommandId.CHOOSE_FREE_PROFILE,
        "Shift+F6": CommandId.CHOOSE_LOCAL,
        "Ctrl+D": CommandId.DEFINE_VARIABLES,
        "Ctrl+I": CommandId.SESSION_INFO,
    }
    for shortcut, command in expected.items():
        assert window._shortcuts.get(shortcut) is command, shortcut
        labels = [item.GetItemLabel() for item in window.menus.items[command]]
        assert any(label.endswith(display_shortcut(shortcut, translate)) for label in labels), (
            shortcut
        )


def test_launching_a_program_puts_the_focus_and_the_caret_on_its_command_line(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("first")
    launcher.transport.receive(b"one" + bytes([10]))
    window.presenter.tick()
    launcher.transport.exit(0)
    window.presenter.tick()
    pump()
    window.command.focus_field()
    window.presenter.submit("second")
    pump()
    assert wx.Window.FindFocus() is window.output
    assert window.output.caret_index() == window.output.text.index("# second")


def test_text_sent_to_a_program_puts_the_focus_in_the_output_and_keeps_the_caret(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    run_and_receive(window, launcher, b"one" + bytes([10]))
    window.command.focus_field()
    window.output.SetInsertionPoint(5)
    pump()
    window.presenter.submit("answer")
    pump()
    assert wx.Window.FindFocus() is window.output
    assert window.output.GetInsertionPoint() == 5


def test_the_context_menu_of_the_output_goes_from_title_to_title_with_the_keys_it_shows(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    menu = window.output._context_menu
    assert menu is not None
    labels = [item.GetItemLabel() for item in menu.GetMenuItems()]
    assert "Previous title (1 to 6)\t" + "Shift+T" in labels
    assert "Next title (1 to 6)\t" + "T" in labels
    assert not item_enabled(window, CommandId.NEXT_TITLE)  # nothing to go through yet
    run_and_receive(window, launcher, b"reply\n")
    launcher.transport.exit(0)
    pump()
    window.presenter.submit("git log")
    run_and_receive(window, launcher, b"commit abc\n")
    assert item_enabled(window, CommandId.PREVIOUS_TITLE)
    window.output.SetInsertionPoint(0)
    window.actions.run(CommandId.NEXT_TITLE)
    assert window.output.GetInsertionPoint() == window.output.GetValue().index("# git log")
    window.actions.run(CommandId.PREVIOUS_TITLE)
    assert window.output.GetInsertionPoint() == 0


def test_the_title_keys_and_the_menu_items_are_one_command(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    window.actions.title_key(None, False)  # no output: refused, as the item is
    assert sink.messages == ["The output is empty."]
    run_and_receive(window, launcher, b"reply\n")
    launcher.transport.exit(0)
    pump()
    window.presenter.submit("git log")
    run_and_receive(window, launcher, b"commit abc\n")
    window.output.SetInsertionPoint(0)
    window.actions.title_key(None, False)  # the key T
    assert window.output.GetInsertionPoint() == window.output.GetValue().index("# git log")
    window.actions.title_key(1, True)  # a key 1 to 6 goes back to the title of that level
    assert window.output.GetInsertionPoint() == 0


def test_the_multi_line_input_sends_its_lines_and_escape_keeps_them_for_next_time(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("python")
    pump()
    outcomes = [(wx.ID_CANCEL, "x\ny"), (wx.ID_OK, "x\ny"), (wx.ID_CANCEL, "")]
    opened: list[str] = []

    def show(dialog: MultilineDialog) -> int:
        opened.append(dialog.value())
        code, text = outcomes.pop(0)
        dialog.text.SetValue(text)
        return int(code)

    monkeypatch.setattr(MultilineDialog, "ShowModal", show)
    window.actions.run(CommandId.MULTILINE)  # Escape: nothing is sent, the lines are kept
    assert launcher.transport.written == []
    window.actions.run(CommandId.MULTILINE)  # it opens on them; Send
    assert opened == ["", "x\ny"]
    assert len(launcher.transport.written) == 1
    assert launcher.transport.written[0].count(b"x") == 1
    assert launcher.transport.written[0].count(b"y") == 1
    window.actions.run(CommandId.MULTILINE)  # sent: the draft is gone
    assert opened[2] == ""


def test_picking_a_block_in_the_history_opens_the_multi_line_box_without_a_crash(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    """Two real boxes one after the other: the focus given back after the first used to abort."""
    window.presenter.submit("a" + chr(10) + "b")
    pump()
    launcher.transport.exit(0)
    pump()
    opened: list[type] = []

    def top(kind: type) -> wx.Dialog | None:
        return next((w for w in wx.GetTopLevelWindows() if isinstance(w, kind)), None)

    def pick() -> None:
        dialog = top(wx.SingleChoiceDialog)
        if dialog is None:
            wx.CallLater(50, pick)
            return
        opened.append(wx.SingleChoiceDialog)
        dialog.EndModal(wx.ID_OK)
        wx.CallLater(100, leave)

    def leave() -> None:
        dialog = top(MultilineDialog)
        if dialog is None:
            wx.CallLater(50, leave)
            return
        opened.append(MultilineDialog)
        assert isinstance(dialog, MultilineDialog)
        assert dialog.value() == "a" + chr(10) + "b"
        dialog.EndModal(wx.ID_CANCEL)

    wx.CallLater(50, pick)
    window.actions.show_history()
    for _ in range(40):  # the box is opened after the list is gone
        if len(opened) == 2:
            break
        pump()
    assert opened == [wx.SingleChoiceDialog, MultilineDialog]


def test_the_commands_and_the_boxes_are_written_in_the_log_at_debug_level(
    window: MainWindow, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.DEBUG)
    window.actions.run(CommandId.SELECT_ALL)
    monkeypatch.setattr(MultilineDialog, "ShowModal", lambda self: wx.ID_CANCEL)
    window.actions.run(CommandId.MULTILINE)
    assert "Command: SELECT_ALL" in caplog.text
    assert "Command: MULTILINE" in caplog.text
    assert "Dialog opened: MultilineDialog" in caplog.text
    assert "Dialog closed: MultilineDialog (5101)" in caplog.text


def test_an_ampersand_of_a_profile_name_stays_in_the_label_of_the_field(
    window: MainWindow,
) -> None:
    window.command.set_input_mode(InputMode.COMMAND, "dev&ops")
    assert window.command._label.GetLabelText() == "dev&ops"
