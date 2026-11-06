"""The Profile menu of the main window: the choice, what it greys, what it sets, the deletion."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.__main__ import open_launch_file
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.launch_file import LaunchFile
from n5terminal.core.config.profiles import Profile, ProfileStore
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import LAUNCH_PROGRAM_COMMAND
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.command_shortcuts import COMMAND_OF_SHORTCUT
from n5terminal.core.session.session_state import CommandId, Interpreter
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    profiles = tmp_path / "profiles"
    store = ProfileStore(profiles)
    store.save(
        Profile("npm", terminal_view_only=True, terminal_size="100x30", commands=["npm test"])
    )
    store.save(Profile("git", interpreter="cmd", commands=["git status"]))
    return profiles


@pytest.fixture
def window(app: wx.App, tmp_path: Path, folder: Path) -> Iterator[MainWindow]:
    frame = MainWindow(
        Settings.load(None), FakeLauncher(), tmp_path, AppContext(profiles_folder=folder)
    )
    frame.Show()
    yield frame
    frame.Close(force=True)


def item_enabled(window: MainWindow, command: CommandId) -> bool:
    return all(item.IsEnabled() for item in window.menus.items[command])


def test_the_profiles_are_listed_by_name(window: MainWindow) -> None:
    assert window.actions.profile_names() == ["git", "npm"]


def test_the_free_profile_is_the_start_and_cannot_be_deleted(window: MainWindow) -> None:
    assert window.actions.current_profile() is None
    assert item_enabled(window, CommandId.SET_PROFILE)
    assert not item_enabled(window, CommandId.DELETE_PROFILE)


def test_a_profile_greys_the_mode_and_the_interpreter_and_sets_the_view(
    window: MainWindow,
) -> None:
    window.actions.profile_names()
    window.actions.choose_profile("npm")
    assert window.actions.current_profile() == "npm"
    assert not item_enabled(window, CommandId.SET_MODE)
    assert not item_enabled(window, CommandId.SET_INTERPRETER)
    assert item_enabled(window, CommandId.SET_SIZE)
    assert item_enabled(window, CommandId.DELETE_PROFILE)
    assert window.GetStatusBar().GetStatusText(1) == "Ready"
    assert window.GetTitle() == f"MiTerm-N5: npm in {window.presenter.working_folder.name}"
    assert window.menus.choices["size"][TerminalSize(100, 30)].IsChecked()
    assert window.menus.toggles[CommandId.SET_TERMINAL_VIEW].IsChecked()


def test_the_terminal_view_is_off_by_default_and_the_item_sets_the_output(
    window: MainWindow,
) -> None:
    item = window.menus.toggles[CommandId.SET_TERMINAL_VIEW]
    assert not item.IsChecked()
    assert window.output.show_history
    window.actions.set_terminal_view_only(True)
    assert not window.output.show_history


def test_the_interpreter_of_the_profile_is_checked(window: MainWindow) -> None:
    window.actions.profile_names()
    window.actions.choose_profile("git")
    assert window.presenter.state.interpreter is Interpreter.CMD
    assert window.menus.choices["interpreter"][Interpreter.CMD].IsChecked()


def test_the_free_profile_keeps_the_values_and_releases_the_menus(window: MainWindow) -> None:
    window.actions.profile_names()
    window.actions.choose_profile("git")
    window.actions.choose_profile(None)
    assert window.presenter.state.interpreter is Interpreter.CMD
    assert window.actions.current_profile() is None
    assert item_enabled(window, CommandId.SET_INTERPRETER)
    assert not item_enabled(window, CommandId.SET_MODE)  # the shell it keeps is always a TUI


def test_a_profile_that_vanished_is_ignored(window: MainWindow, folder: Path) -> None:
    window.actions.profile_names()
    window.actions.choose_profile("missing")
    assert window.actions.current_profile() is None


def test_the_commands_of_the_profile_are_offered(window: MainWindow) -> None:
    window.actions.profile_names()
    window.actions.choose_profile("npm")
    assert window.presenter.profile_values.commands() == ["npm test"]


# The launch file ---------------------------------------------------------------------------------


def test_the_launch_file_chooses_the_profile_and_gives_its_variables(window: MainWindow) -> None:
    launch = LaunchFile(profile="NPM", variables={"name": "dev"})
    assert window.actions.apply_launch_file(launch) == []
    assert window.actions.current_profile() == "npm"  # the name as the file of the profile has it
    assert window.presenter.profile_values.get("npm") == {"name": "dev"}


def test_a_launch_file_without_profile_changes_nothing(window: MainWindow) -> None:
    assert window.actions.apply_launch_file(LaunchFile()) == []
    assert window.actions.current_profile() is None


def test_a_profile_that_does_not_exist_is_reported_and_the_free_profile_stays(
    window: MainWindow,
) -> None:
    problems = window.actions.apply_launch_file(LaunchFile(profile="missing"))
    assert problems == ["The profile missing does not exist."]
    assert window.actions.current_profile() is None


def test_an_unreadable_launch_file_is_reported_and_asks_for_nothing(tmp_path: Path) -> None:
    launch, problems = open_launch_file(tmp_path / "missing.n5term")
    assert launch == LaunchFile()
    assert len(problems) == 1


def test_launch_the_program_is_greyed_until_a_profile_with_a_program_is_chosen(
    window: MainWindow,
) -> None:
    assert not item_enabled(window, CommandId.LAUNCH_PROGRAM)  # the free profile
    window.presenter.select_profile(Profile("npm", commands=["npm test"]))
    assert not item_enabled(window, CommandId.LAUNCH_PROGRAM)  # no program
    window.presenter.select_profile(Profile("git", program="git", commands=["status"]))
    assert item_enabled(window, CommandId.LAUNCH_PROGRAM)


def test_f5_stands_for_launching_the_program() -> None:
    assert COMMAND_OF_SHORTCUT["profile.launch"] is CommandId.LAUNCH_PROGRAM
    assert LAUNCH_PROGRAM_COMMAND.default == "F5"


def test_no_launch_file_means_no_problem() -> None:
    assert open_launch_file(None) == (LaunchFile(), [])


def test_the_warnings_of_the_file_are_handed_on(tmp_path: Path) -> None:
    path = tmp_path / "x.n5term"
    path.write_text("WorkingPath = nowhere\n", encoding="utf-8")
    launch, problems = open_launch_file(path)
    assert launch.folder is None
    assert problems == launch.warnings != []


def test_the_powershell_selection_stays_available_while_a_profile_is_chosen(
    window: MainWindow,
) -> None:
    window.actions.choose_profile("npm")
    assert item_enabled(window, CommandId.SELECT_POWERSHELL)
    assert not item_enabled(window, CommandId.SET_INTERPRETER)


def test_the_application_starts_on_the_startup_profile(window: MainWindow) -> None:
    assert window.actions.apply_startup_profile("npm") == []
    assert window.actions.current_profile() == "npm"
    assert window.menus.toggles[CommandId.SET_TERMINAL_VIEW].IsChecked()


def test_without_a_startup_profile_the_free_profile_stays(window: MainWindow) -> None:
    assert window.actions.apply_startup_profile("") == []
    assert window.actions.current_profile() is None


def test_a_startup_profile_that_is_gone_leaves_the_free_profile_and_says_so(
    window: MainWindow,
) -> None:
    problems = window.actions.apply_startup_profile("gone")
    assert problems == ["The startup profile gone does not exist."]
    assert window.actions.current_profile() is None


def test_the_key_of_the_launch_command_is_bound_and_runs_it(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert window._shortcuts["F5"] is CommandId.LAUNCH_PROGRAM
    ran: list[CommandId] = []
    monkeypatch.setattr(window.actions, "run", ran.append)
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_F5)
    window._on_char_hook(event)
    assert ran == [CommandId.LAUNCH_PROGRAM]


def test_a_profile_file_that_cannot_be_read_is_a_warning_of_the_window(
    app: wx.App, tmp_path: Path, folder: Path
) -> None:
    (folder / "broken.json").write_text("{not json", encoding="utf-8")
    frame = MainWindow(
        Settings.load(None), FakeLauncher(), tmp_path, AppContext(profiles_folder=folder)
    )
    try:
        assert len(frame.profile_warnings) == 1
        assert "broken" in frame.profile_warnings[0]
    finally:
        frame.Close(force=True)
        wx.Yield()
