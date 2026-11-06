"""The "Mask the message" box beside the Send button: what a window can get wrong about it."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.settings import Settings
from n5terminal.ui.hidden_text import is_text_hidden
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui

SECRET = "hunter2-p4ss"


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


def tick_box(window: MainWindow, ticked: bool) -> None:
    """Tick or untick the box as a click would: the box changes, then it tells its handler."""
    box = window.command.hide_box
    box.SetValue(ticked)
    event = wx.CommandEvent(wx.wxEVT_CHECKBOX, box.GetId())
    event.SetEventObject(box)
    event.SetInt(int(ticked))
    box.GetEventHandler().ProcessEvent(event)


def type_hidden(window: MainWindow, text: str) -> None:
    tick_box(window, True)
    window.command.field.SetValue(text)


def test_the_box_has_a_name_and_is_greyed_while_a_command_is_typed(window: MainWindow) -> None:
    assert window.command.hide_box.GetLabel() == "Mask the message"
    assert not window.command.hide_box.IsEnabled()
    assert not window.command.hide_box.GetValue()


def test_the_box_is_available_while_a_program_runs_and_greyed_again_at_its_end(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    pump()
    assert window.command.hide_box.IsEnabled()
    launcher.transport.exit(0)
    pump()
    assert not window.command.hide_box.IsEnabled()


@pytest.mark.skipif(sys.platform != "win32", reason="the field of Windows")
def test_ticking_the_box_makes_the_field_a_password_field_and_unticking_gives_it_back(
    window: MainWindow,
) -> None:
    window.presenter.submit("ping host")
    pump()
    window.command.field.SetValue(SECRET)
    assert not is_text_hidden(window.command.field)
    type_hidden(window, SECRET)
    assert is_text_hidden(window.command.field)  # what a screen reader looks at
    assert window.command.field.GetValue() == SECRET  # the text is there, only hidden
    tick_box(window, False)
    assert not is_text_hidden(window.command.field)


@pytest.mark.skipif(sys.platform != "win32", reason="the field of Windows")
def test_a_hidden_message_is_sent_hidden_and_the_box_clears_itself(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    pump()
    type_hidden(window, SECRET)
    window.command._send()
    window.presenter.tick()
    pump()
    assert launcher.transport.written == [f"{SECRET}\n".encode()]
    assert SECRET not in window.output.GetValue()  # not echoed in the output
    assert "> (hidden message)" in window.output.GetValue()
    assert window.command.field.GetValue() == ""
    assert not window.command.hide_box.GetValue()  # the next message is not hidden by mistake
    assert not is_text_hidden(window.command.field)
    assert window.command.hide_box.IsEnabled()  # the program still runs


@pytest.mark.skipif(sys.platform != "win32", reason="the field of Windows")
def test_the_box_does_not_stay_ticked_when_the_program_ends(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    pump()
    type_hidden(window, SECRET)
    launcher.transport.exit(0)
    pump()
    assert not window.command.hide_box.GetValue()
    assert not is_text_hidden(window.command.field)


def test_a_message_that_is_not_hidden_is_sent_as_before(
    window: MainWindow, launcher: FakeLauncher
) -> None:
    window.presenter.submit("ping host")
    pump()
    window.command.field.SetValue("answer")
    window.command._send()
    window.presenter.tick()
    pump()
    assert launcher.transport.written == [b"answer\n"]
    assert "> answer" in window.output.GetValue()
