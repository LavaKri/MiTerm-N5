"""The commands that change a setting, driven through the main window: Preferences, PowerShell.

The dialogs themselves are tested on their own; here the window opens them with what it knows (the
profiles, the settings), and keeps or drops what they return. ``Feedback.modal`` is replaced, so no
dialog is really shown: ``act`` plays what the user does in it.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.profiles import Profile, ProfileStore
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import CommandId
from n5terminal.ui.main_window import MainWindow
from n5terminal.ui.powershell_dialog import PowerShellDialog
from n5terminal.ui.preferences_dialog import PreferencesDialog

pytestmark = pytest.mark.ui

OLD_POWERSHELL = r"C:\old\pwsh.exe"


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "settings.json"


@pytest.fixture
def window(app: wx.App, tmp_path: Path, store: Path) -> Iterator[MainWindow]:
    profiles = ProfileStore(tmp_path / "profiles")
    profiles.save(Profile("git"))
    profiles.save(Profile("npm"))
    settings = Settings.load(store)
    settings.powershell_path = OLD_POWERSHELL
    context = AppContext(profiles_folder=tmp_path / "profiles")
    frame = MainWindow(settings, FakeLauncher(), tmp_path, context)
    yield frame
    frame.Close(force=True)
    wx.Yield()  # wx destroys a top-level window later: let it do it before the next test


def answer(
    monkeypatch: pytest.MonkeyPatch,
    window: MainWindow,
    result: int,
    act: Callable[[wx.Dialog], None] = lambda dialog: None,
) -> None:
    """The next dialog the window shows: ``act`` is what the user does, ``result`` how it closes."""

    def modal(dialog: wx.Dialog) -> int:
        act(dialog)
        return result

    monkeypatch.setattr(window.feedback, "modal", modal)


def test_the_preferences_offer_the_profiles_of_the_window(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    offered: list[list[str]] = []

    def look(dialog: wx.Dialog) -> None:
        assert isinstance(dialog, PreferencesDialog)
        offered.append(dialog.general_page.startup_profile.GetStrings())

    answer(monkeypatch, window, wx.ID_CANCEL, look)
    window.actions.run(CommandId.PREFERENCES)
    assert offered == [["Free", "git", "npm"]]


def test_accepted_preferences_are_applied_and_saved(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, store: Path
) -> None:
    limits: list[int] = []
    monkeypatch.setattr(window.output, "set_limit", limits.append)

    def choose(dialog: wx.Dialog) -> None:
        assert isinstance(dialog, PreferencesDialog)
        dialog.general_page.limit.SetValue(5_000)

    answer(monkeypatch, window, wx.ID_OK, choose)
    window.actions.run(CommandId.PREFERENCES)
    assert limits == [5_000]
    assert Settings.load(store).output_limit == 5_000


def test_cancelled_preferences_change_and_save_nothing(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, store: Path
) -> None:
    def choose(dialog: wx.Dialog) -> None:
        assert isinstance(dialog, PreferencesDialog)
        dialog.general_page.limit.SetValue(5_000)

    answer(monkeypatch, window, wx.ID_CANCEL, choose)
    window.actions.run(CommandId.PREFERENCES)
    assert window.actions._settings.output_limit != 5_000
    assert not store.exists()


def test_an_accepted_powershell_is_chosen_and_saved(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, store: Path
) -> None:
    def choose(dialog: wx.Dialog) -> None:
        assert isinstance(dialog, PowerShellDialog)
        assert dialog.path.GetValue() == OLD_POWERSHELL  # "Other…" shows the path in use
        dialog.versions.SetSelection(0)  # Windows PowerShell

    answer(monkeypatch, window, wx.ID_OK, choose)
    window.actions.run(CommandId.SELECT_POWERSHELL)
    assert window.presenter.powershell_path == ""
    assert Settings.load(store).powershell_path == ""


def test_a_cancelled_powershell_changes_and_saves_nothing(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, store: Path
) -> None:
    def choose(dialog: wx.Dialog) -> None:
        assert isinstance(dialog, PowerShellDialog)
        dialog.versions.SetSelection(0)

    answer(monkeypatch, window, wx.ID_CANCEL, choose)
    window.actions.run(CommandId.SELECT_POWERSHELL)
    assert window.presenter.powershell_path == OLD_POWERSHELL
    assert not store.exists()
