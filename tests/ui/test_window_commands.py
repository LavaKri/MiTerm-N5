"""Commands of the main window that ask or show something: the history, a new session, quitting.

Driven through the window (``actions.run``, ``Close``): the dialogs are replaced by answers, so that
nothing is shown and no program starts. The rules behind them are tested in ``tests/presenters``.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import NewSessionError
from n5terminal.core.session.session_state import CommandId
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui

QUESTION = "A program is running. Stop it and quit?"


def pump() -> None:
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.Yield()


@pytest.fixture
def launcher() -> FakeLauncher:
    return FakeLauncher()


@pytest.fixture
def data_folder(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def window(
    app: wx.App, launcher: FakeLauncher, tmp_path: Path, data_folder: Path
) -> Iterator[MainWindow]:
    frame = MainWindow(Settings.load(None), launcher, tmp_path, AppContext(data_folder=data_folder))
    frame.Show()
    pump()
    yield frame
    if frame:  # a test that quits has destroyed it already
        frame.Close(force=True)
    wx.Yield()


def recording(window: MainWindow) -> RecordingMessageSink:
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    return sink


def answer_to_confirm(asked: list[str], reply: bool) -> Callable[[str, str], bool]:
    """A ``Feedback.confirm`` that notes the question and answers ``reply``."""

    def confirm(title: str, message: str) -> bool:
        asked.append(message)
        return reply

    return confirm


def type_and_end(window: MainWindow, launcher: FakeLauncher, *lines: str) -> None:
    """Launch each command and let its program end, so that the history keeps them."""
    for line in lines:
        window.presenter.submit(line)
        launcher.transport.exit(0)
        pump()
        window.presenter.tick()


# History (Ctrl+Space) ---------------------------------------------------------------------------


def test_an_empty_history_is_announced(window: MainWindow) -> None:
    sink = recording(window)
    window.actions.run(CommandId.HISTORY)
    assert sink.messages == ["No command typed yet."]


def test_the_history_offers_the_commands_typed_and_puts_the_pick_in_the_field(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    type_and_end(window, launcher, "first", "second")
    asked: list[tuple[list[str], int]] = []

    def choose(title: str, prompt: str, labels: list[str], selected: int = 0) -> int | None:
        asked.append((labels, selected))
        return 0

    monkeypatch.setattr(window.feedback, "choose", choose)
    window.actions.run(CommandId.HISTORY)
    assert asked == [(["first", "second"], 1)]  # the last command typed is selected
    assert window.command.field.GetValue() == "first"


def test_a_cancelled_history_leaves_the_field_alone(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    type_and_end(window, launcher, "first")
    window.command.field.SetValue("half typed")
    monkeypatch.setattr(window.feedback, "choose", lambda *args: None)
    window.actions.run(CommandId.HISTORY)
    assert window.command.field.GetValue() == "half typed"


# A new session (Ctrl+N) -------------------------------------------------------------------------


def test_a_new_session_starts_in_the_working_folder_with_the_data_folder_given(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, data_folder: Path
) -> None:
    started: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "n5terminal.ui.actions.start_new_session", lambda *args: started.append(args)
    )
    window.actions.run(CommandId.NEW_SESSION)
    assert started == [(tmp_path, data_folder, False)]


def test_a_new_session_that_cannot_start_is_announced_with_its_cause(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object) -> None:
        raise NewSessionError("no room")

    errors: list[str] = []
    monkeypatch.setattr("n5terminal.ui.actions.start_new_session", refuse)
    monkeypatch.setattr(window.feedback, "show_error", errors.append)
    window.actions.run(CommandId.NEW_SESSION)
    assert errors == ["A new session could not be started.\nno room"]


# Quitting ---------------------------------------------------------------------------------------


def test_quitting_with_a_program_running_asks_and_a_no_keeps_everything(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("ping host")
    asked: list[str] = []
    monkeypatch.setattr(window.feedback, "confirm", answer_to_confirm(asked, False))
    assert not window.Close()
    assert asked == [QUESTION]
    assert window  # still there
    assert not launcher.transport.closed  # the program goes on


def test_quitting_with_a_program_running_and_a_yes_stops_the_program(
    window: MainWindow, launcher: FakeLauncher, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("ping host")
    monkeypatch.setattr(window.feedback, "confirm", lambda title, message: True)
    assert window.Close()
    pump()  # wx destroys a top-level window later
    assert launcher.transport.closed
    assert not window  # destroyed


def test_quitting_with_no_program_asks_nothing(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(window.feedback, "confirm", answer_to_confirm(asked, True))
    assert window.Close()
    pump()  # wx destroys a top-level window later
    assert asked == []


def test_a_second_close_before_the_window_is_destroyed_does_nothing(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """wx destroys a top-level window later: a second close (Alt+F4 twice) can come before."""
    released: list[str] = []
    release = window.feedback.close

    def count_and_release() -> None:
        released.append("released")
        release()

    monkeypatch.setattr(window.feedback, "close", count_and_release)
    assert window.Close()
    assert window.Close()  # the window still exists, as wx has not run its idle time yet
    pump()
    assert released == ["released"]  # the sink is released once, not twice
