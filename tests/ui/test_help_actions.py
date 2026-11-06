"""Help > Open the help (F1) and Develop > Convert the help to HTML in the main window."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from fakes.recording_sinks import RecordingMessageSink
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.command_shortcuts import COMMAND_OF_SHORTCUT
from n5terminal.core.session.session_state import CommandId
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


@pytest.fixture
def help_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "Help"
    folder.mkdir()
    return folder


@pytest.fixture
def window(app: wx.App, tmp_path: Path, help_folder: Path) -> Iterator[MainWindow]:
    settings = Settings.load(None)
    frame = MainWindow(settings, FakeLauncher(), tmp_path, AppContext(help_folder=help_folder))
    yield frame
    frame.Close(force=True)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The addresses the browser is asked to open (it is not really opened)."""
    addresses: list[str] = []

    def open_address(address: str) -> bool:
        addresses.append(address)
        return True

    monkeypatch.setattr("webbrowser.open", open_address)
    return addresses


def recording(window: MainWindow) -> RecordingMessageSink:
    sink = RecordingMessageSink()
    window.feedback.announcements.message_sink = sink
    return sink


def test_the_page_of_the_language_opens_in_the_browser(
    window: MainWindow, help_folder: Path, opened: list[str]
) -> None:
    (help_folder / "Fr.html").write_text("fr", encoding="utf-8")
    (help_folder / "En.html").write_text("en", encoding="utf-8")
    window.actions.run(CommandId.OPEN_HELP)
    assert opened == [(help_folder / "Fr.html").as_uri()]
    window.actions._settings.language = "en"
    window.actions.run(CommandId.OPEN_HELP)
    assert opened[-1] == (help_folder / "En.html").as_uri()


def test_a_missing_page_is_announced(window: MainWindow, opened: list[str]) -> None:
    sink = recording(window)
    window.actions.run(CommandId.OPEN_HELP)
    assert opened == []
    assert sink.messages == ["The help file Fr.html was not found."]


def test_a_browser_that_does_not_open_is_announced(
    window: MainWindow, help_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (help_folder / "Fr.html").write_text("fr", encoding="utf-8")
    monkeypatch.setattr("webbrowser.open", lambda address: False)
    sink = recording(window)
    window.actions.run(CommandId.OPEN_HELP)
    assert sink.messages == ["The help could not be opened in the browser."]


def test_the_help_is_always_available_and_has_its_shortcut(window: MainWindow) -> None:
    assert all(item.IsEnabled() for item in window.menus.items[CommandId.OPEN_HELP])
    assert COMMAND_OF_SHORTCUT["help.open"] is CommandId.OPEN_HELP


def test_the_conversion_writes_the_pages_and_says_how_many(
    window: MainWindow, help_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (help_folder / "Fr.md").write_text("# Aide\n", encoding="utf-8")
    shown: list[str] = []
    monkeypatch.setattr(window.feedback, "show_info", shown.append)
    window.actions.run(CommandId.CONVERT_HELP)
    assert (help_folder / "Fr.html").is_file()
    assert shown == ["Help converted: 1 pages."]


def test_a_conversion_that_fails_is_shown_as_an_error(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors: list[str] = []
    monkeypatch.setattr(window.feedback, "show_error", errors.append)
    window.actions.run(CommandId.CONVERT_HELP)  # no .md file in the folder
    assert len(errors) == 1
    assert errors[0].startswith("The help could not be converted.")
