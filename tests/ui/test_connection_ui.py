"""The Connection menu, its dialogs, and the dialogs of ``ssh``: what a window can get wrong."""

import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.connections import Connection, ConnectionStore
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import CommandId, Phase
from n5terminal.presenters.connection_editor import ConnectionEditor
from n5terminal.presenters.ssh_choice import SshChoice
from n5terminal.ui.connection_dialog import ConnectionDialog
from n5terminal.ui.connection_prompts import ConnectionPrompts, HostKeyDialog, SecretDialog
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.main_window import MainWindow
from n5terminal.ui.ssh_dialog import SshDialog

pytestmark = pytest.mark.ui

PROD = Connection("prod", target="admin@example.org", port=2222)


def pump() -> None:
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.Yield()


@pytest.fixture
def launcher() -> FakeLauncher:
    return FakeLauncher()


@pytest.fixture
def window(app: wx.App, launcher: FakeLauncher, tmp_path: Path) -> Iterator[MainWindow]:
    folder = tmp_path / "connections"
    ConnectionStore(folder).save(PROD)
    context = AppContext(connections_folder=folder)
    frame = MainWindow(Settings.load(None), launcher, tmp_path, context)
    frame.Show()
    pump()
    yield frame
    frame.Close(force=True)


def enabled(window: MainWindow, command: CommandId) -> bool:
    return all(item.IsEnabled() for item in window.menus.items[command])


# The menu --------------------------------------------------------------------------------------


def test_the_connection_menu_is_between_profile_and_terminal(window: MainWindow) -> None:
    titles = [title.replace("&", "") for _menu, title in window.GetMenuBar().GetMenus()]
    assert titles.index("Connection") == titles.index("Profile") + 1
    assert titles.index("Terminal") == titles.index("Connection") + 1


def test_with_locale_only_choosing_adding_and_the_client_are_available(window: MainWindow) -> None:
    for command in (CommandId.SET_CONNECTION, CommandId.ADD_CONNECTION, CommandId.SELECT_SSH):
        assert enabled(window, command), command
    for command in (
        CommandId.CONNECT,
        CommandId.DISCONNECT,
        CommandId.EDIT_CONNECTION,
        CommandId.DELETE_CONNECTION,
    ):
        assert not enabled(window, command), command


def test_choosing_a_connection_opens_what_it_allows_and_greys_the_local_commands(
    window: MainWindow,
) -> None:
    assert window.actions.connection_names() == ["prod"]
    window.actions.choose_connection("prod")
    pump()
    assert window.actions.current_connection() == "prod"
    assert enabled(window, CommandId.CONNECT)
    assert enabled(window, CommandId.EDIT_CONNECTION)
    assert not enabled(window, CommandId.CHOOSE_FOLDER)
    assert not enabled(window, CommandId.SET_INTERPRETER)
    assert not enabled(window, CommandId.DISCONNECT)
    assert window.GetTitle() == "MiTerm-N5: free profile on SSH prod (not connected)"


def test_a_connection_that_went_away_is_not_chosen(window: MainWindow, tmp_path: Path) -> None:
    window.actions.choose_connection("missing")
    assert window.actions.current_connection() is None


def test_the_menu_command_connects_and_the_connection_greys_the_menu(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.actions.choose_connection("prod")
    window.actions.run(CommandId.CONNECT)
    pump()
    assert launcher.connections[0].connection.name == "prod"
    assert window.presenter.state.phase is Phase.RUNNING
    assert enabled(window, CommandId.DISCONNECT)
    for command in (CommandId.SET_CONNECTION, CommandId.ADD_CONNECTION, CommandId.SELECT_SSH):
        assert not enabled(window, command), command
    assert not enabled(window, CommandId.CONNECT)


def test_entering_in_the_command_field_opens_the_connection(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.actions.choose_connection("prod")
    window.command.field.SetValue("uptime")
    window.command._send()
    pump()
    assert len(launcher.connections) == 1
    assert launcher.transport.written == [b"uptime\r"]  # sent once connected
    assert window.command.field.GetValue() == ""


def test_the_output_names_the_connection_and_the_title_of_the_window_follows(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.actions.choose_connection("prod")
    window.actions.run(CommandId.CONNECT)
    window.presenter.tick()
    pump()
    assert window.output.GetValue().startswith("# SSH prod\nTo admin@example.org:2222")
    assert window.GetTitle() == "MiTerm-N5: free profile on SSH prod"


def test_the_end_of_the_connection_is_the_last_line_after_the_screen(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.actions.choose_connection("prod")
    window.actions.run(CommandId.CONNECT)
    launcher.transport.receive(b"hello\r\n")
    window.presenter.tick()
    launcher.transport.exit(255)
    pump()  # the end reaches the presenter through the UI thread
    window.presenter.tick()
    pump()
    text = window.output.GetValue()
    assert text.endswith("\nDisconnected (code 255).")
    assert "hello" in text
    assert window.output.live_end_index() == len(text) - len("\nDisconnected (code 255).")


def test_a_connection_is_deleted_after_a_confirmation(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    window.actions.choose_connection("prod")
    monkeypatch.setattr(window.feedback, "confirm", lambda title, question: True)
    window.actions.run(CommandId.DELETE_CONNECTION)
    pump()
    assert window.actions.current_connection() is None
    assert window.actions.connection_names() == []
    assert not (tmp_path / "connections" / "prod.json").exists()


def test_a_connection_is_not_deleted_when_the_user_says_no(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.actions.choose_connection("prod")
    monkeypatch.setattr(window.feedback, "confirm", lambda title, question: False)
    window.actions.run(CommandId.DELETE_CONNECTION)
    assert window.actions.current_connection() == "prod"


# The connection dialog -------------------------------------------------------------------------


def make_dialog(connection: Connection, existing: list[str]) -> tuple[wx.Frame, ConnectionDialog]:
    frame = wx.Frame(None)
    editor = ConnectionEditor(connection, existing, lambda text: text)
    return frame, ConnectionDialog(frame, editor)


@pytest.fixture
def dialog(app: wx.App) -> Iterator[ConnectionDialog]:
    frame, box = make_dialog(PROD, ["prod", "nas"])
    yield box
    box.Destroy()
    frame.Destroy()


def test_each_label_comes_right_before_its_control(dialog: ConnectionDialog) -> None:
    for control, label in (
        (dialog.name, "Name"),
        (dialog.target, "Target (an alias or user@host)"),
        (dialog.port, "Port (optional)"),
    ):
        previous = control.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == label
        assert control.GetName() == label


def test_the_dialog_starts_on_the_values_of_the_connection(dialog: ConnectionDialog) -> None:
    assert (dialog.name.GetValue(), dialog.target.GetValue(), dialog.port.GetValue()) == (
        "prod",
        "admin@example.org",
        "2222",
    )
    assert dialog.GetTitle() == "Edit the connection prod"


def test_a_new_connection_has_its_own_title_and_empty_fields(app: wx.App) -> None:
    frame, box = make_dialog(Connection(""), [])
    try:
        assert box.GetTitle() == "New connection"
        assert box.name.GetValue() == box.target.GetValue() == box.port.GetValue() == ""
    finally:
        box.Destroy()
        frame.Destroy()


def test_commit_hands_the_controls_to_the_draft(dialog: ConnectionDialog) -> None:
    dialog.name.SetValue("  web ")
    dialog.target.SetValue(" me@web.example ")
    dialog.port.SetValue(" 22 ")
    dialog.commit()
    connection = dialog._editor.build()
    assert (connection.name, connection.target, connection.port) == ("web", "me@web.example", 22)


# The dialogs of ssh ----------------------------------------------------------------------------


def test_the_host_key_dialog_reads_first_and_cancels_by_default(app: wx.App) -> None:
    frame = wx.Frame(None)
    box = HostKeyDialog(frame, "Connection to prod", "admin@example.org, port 2222", "Trust it?")
    try:
        assert box.GetTitle() == "Connection to prod"
        assert box.text.GetValue() == "Trust it?"
        assert box.text.GetWindowStyle() & wx.TE_READONLY
        assert box.cancel.GetLabel() == "Cancel"
        assert box.trust.GetLabel() == "Trust and continue"
        assert box.GetEscapeId() == wx.ID_CANCEL
        assert box.GetDefaultItem() is box.cancel
    finally:
        box.Destroy()
        frame.Destroy()


def test_the_secret_dialog_hides_what_is_typed_and_names_the_question(app: wx.App) -> None:
    frame = wx.Frame(None)
    box = SecretDialog(frame, "Connection to prod", "admin@example.org", "admin's password: ")
    try:
        assert box.secret.GetWindowStyle() & wx.TE_PASSWORD
        assert box.secret.GetName() == "admin's password:"
        previous = box.secret.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == "admin's password:"
        labels = [
            child.GetLabel() for child in box.GetChildren() if isinstance(child, wx.StaticText)
        ]
        assert any("password" in label and "hidden" in label for label in labels)
    finally:
        box.Destroy()
        frame.Destroy()


def run_in_dialog(
    prompts: ConnectionPrompts, frame: wx.Frame, close_with: Callable[[wx.Dialog], None]
) -> None:
    """Close the dialog the prompts opened as soon as it is shown."""

    def close_when_open() -> None:
        dialog = prompts._open
        if dialog is None:
            wx.CallLater(20, close_when_open)
            return
        close_with(dialog)

    wx.CallLater(20, close_when_open)


def test_the_secret_is_given_back_when_ok_and_none_when_cancelled(app: wx.App) -> None:
    frame = wx.Frame(None)
    frame_prompts = ConnectionPrompts(frame, _feedback_for(frame))
    try:

        def type_and_ok(dialog: wx.Dialog) -> None:
            assert isinstance(dialog, SecretDialog)
            dialog.secret.SetValue("s3cr3t")
            dialog.EndModal(wx.ID_OK)

        run_in_dialog(frame_prompts, frame, type_and_ok)
        assert frame_prompts.ask_secret("t", "w", "password: ") == "s3cr3t"
        run_in_dialog(frame_prompts, frame, lambda dialog: dialog.EndModal(wx.ID_CANCEL))
        assert frame_prompts.ask_secret("t", "w", "password: ") is None
    finally:
        frame.Destroy()


def test_the_host_key_is_trusted_only_by_the_trust_button(app: wx.App) -> None:
    frame = wx.Frame(None)
    prompts = ConnectionPrompts(frame, _feedback_for(frame))
    try:
        run_in_dialog(prompts, frame, lambda dialog: dialog.EndModal(wx.ID_YES))
        assert prompts.confirm_host_key("t", "w", "Trust it?") is True
        run_in_dialog(prompts, frame, lambda dialog: dialog.EndModal(wx.ID_CANCEL))
        assert prompts.confirm_host_key("t", "w", "Trust it?") is False
    finally:
        frame.Destroy()


def test_a_dialog_withdrawn_from_outside_is_a_cancel(app: wx.App) -> None:
    frame = wx.Frame(None)
    prompts = ConnectionPrompts(frame, _feedback_for(frame))
    try:
        run_in_dialog(prompts, frame, lambda _dialog: prompts.withdraw())
        assert prompts.ask_secret("t", "w", "password: ") is None
        prompts.withdraw()  # nothing open: nothing happens
    finally:
        frame.Destroy()


def test_withdrawing_from_the_thread_of_the_transport_goes_through_the_ui_thread(
    app: wx.App,
) -> None:
    """The presenter posts it: the dialog is only ever touched on the UI thread."""
    posted: list[Callable[[], None]] = []
    seen = threading.Event()

    def post(action: Callable[[], None]) -> None:
        posted.append(action)
        seen.set()

    from fakes.fake_view import FakeView  # noqa: PLC0415
    from n5terminal.presenters.connection_interaction import ConnectionInteraction  # noqa: PLC0415

    view = FakeView()
    threading.Thread(
        target=ConnectionInteraction(post, view, "t", "s", "w").withdraw, daemon=True
    ).start()
    assert seen.wait(5)
    assert view.withdrawn_dialogs == 0
    posted[0]()
    assert view.withdrawn_dialogs == 1


def _feedback_for(frame: wx.Frame) -> Feedback:
    return Feedback(frame, Settings.load(None), lambda: False)


# The dialog "OpenSSH client" -------------------------------------------------------------------


def make_ssh(current: str) -> tuple[wx.Frame, SshChoice, SshDialog]:
    frame = wx.Frame(None)
    draft = SshChoice(current, [r"C:\Git\usr\bin\ssh.exe"], lambda text: text, lambda p: bool(p))
    return frame, draft, SshDialog(frame, draft)


def test_the_ssh_dialog_starts_on_the_ssh_of_windows_and_says_what_was_tried(app: wx.App) -> None:
    frame, draft, box = make_ssh("")
    try:
        assert box.GetTitle() == "OpenSSH client"
        assert box.versions.GetStringSelection().startswith("OpenSSH of Windows (default")
        assert box.versions.GetStrings()[1].endswith("(not tried)")
        assert not box.path.IsEnabled()
        notes = [c.GetLabel() for c in box.GetChildren() if isinstance(c, wx.StaticText)]
        assert draft.note in notes
    finally:
        box.Destroy()
        frame.Destroy()


def test_commit_hands_the_ssh_chosen_to_the_draft(app: wx.App) -> None:
    frame, draft, box = make_ssh("")
    try:
        box.versions.SetSelection(1)
        box.commit()
        assert draft.chosen_path() == r"C:\Git\usr\bin\ssh.exe"
    finally:
        box.Destroy()
        frame.Destroy()
