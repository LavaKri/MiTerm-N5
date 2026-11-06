"""The screen reader output of the announcement center: chosen at start, changed, failing."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from n5terminal.core.config.announcements import Announce, NullMessageSink
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import ScreenReaderOutputError
from n5terminal.ui import feedback as feedback_module
from n5terminal.ui.feedback import Feedback
from n5terminal.ui.message_sinks import UiaMessageSink

pytestmark = pytest.mark.ui


@pytest.fixture
def feedback(app: wx.App) -> Iterator[Feedback]:
    frame = wx.Frame(None)
    wx.Panel(frame)
    settings = Settings.load(None)
    result = Feedback(frame, settings, lambda: False)
    result.apply_screen_reader_output(settings.screen_reader_output)
    yield result
    result.close()
    frame.Destroy()


@pytest.fixture
def frame(app: wx.App) -> Iterator[wx.Frame]:
    result = wx.Frame(None)
    wx.Panel(result)
    yield result
    result.Destroy()


def window_exists(sink: UiaMessageSink) -> bool:
    return bool(sink._announcer)


def test_the_default_output_is_ui_automation(feedback: Feedback) -> None:
    assert isinstance(feedback.announcements.message_sink, UiaMessageSink)


def test_an_announcement_goes_through_the_sink(feedback: Feedback) -> None:
    assert feedback.announcements.notify(Announce.HISTORY_EMPTY) is not None


def test_changing_the_output_releases_the_previous_sink(feedback: Feedback) -> None:
    sink = feedback.announcements.message_sink
    assert isinstance(sink, UiaMessageSink)
    feedback.apply_screen_reader_output("none")
    assert isinstance(feedback.announcements.message_sink, NullMessageSink)
    assert not window_exists(sink)


def test_an_output_that_cannot_be_made_is_announced_once_and_replaced_by_none(
    feedback: Feedback, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors: list[str] = []

    def refuse(output_id: str, parent: wx.Window) -> None:
        raise ScreenReaderOutputError("refused")

    monkeypatch.setattr(feedback_module, "create_sink", refuse)
    monkeypatch.setattr(feedback, "show_error", errors.append)
    feedback.apply_screen_reader_output("uia")
    assert isinstance(feedback.announcements.message_sink, NullMessageSink)
    assert len(errors) == 1
    assert "refused" in errors[0]


def test_the_settings_are_written(frame: wx.Frame, tmp_path: Path) -> None:
    store = tmp_path / "settings.json"
    settings = Settings.load(store)
    settings.language = "en"
    Feedback(frame, settings, lambda: False).save_settings()
    assert Settings.load(store).language == "en"


def test_settings_that_cannot_be_written_are_announced_once_and_the_application_goes_on(
    frame: wx.Frame, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors: list[str] = []
    feedback = Feedback(frame, Settings(store=tmp_path), lambda: False)  # a folder: no file there
    monkeypatch.setattr(feedback, "show_error", errors.append)
    feedback.save_settings()
    assert len(errors) == 1
    assert errors[0].startswith("The settings could not be saved.")
    assert str(tmp_path) in errors[0]
