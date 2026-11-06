"""The profile dialog and the Add and Edit items of the Profile menu."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.profiles import CommandUse, Profile, ProfileStore
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import CommandId, LaunchMode
from n5terminal.presenters.profile_editor import ProfileEditor
from n5terminal.ui.main_window import MainWindow
from n5terminal.ui.profile_dialog import ProfileDialog
from n5terminal.ui.variables_dialog import VariablesDialog

pytestmark = pytest.mark.ui


@pytest.fixture
def dialog(app: wx.App) -> Iterator[ProfileDialog]:
    frame = wx.Frame(None)
    profile = Profile("git", interpreter="cmd", variables=["source"], shell_commands=["git status"])
    box = ProfileDialog(frame, ProfileEditor(profile, ["git"], lambda text: text))
    yield box
    box.Destroy()
    frame.Destroy()


def test_each_label_comes_right_before_its_control(dialog: ProfileDialog) -> None:
    for control, label in (
        (dialog.name, "Name"),
        (dialog.program, "Program"),
        (dialog.interpreter, "Interpreter"),
        (dialog.prompt_prefix, "Prompt prefix"),
        (dialog.mode, "Mode"),
        (dialog.size, "Terminal size"),
    ):
        previous = control.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == label
        assert control.GetName() == label


def test_the_dialog_starts_on_the_values_of_the_profile(dialog: ProfileDialog) -> None:
    assert dialog.name.GetValue() == "git"
    assert dialog.interpreter.GetStringSelection() == "Cmd"
    assert not dialog.mode.IsEnabled()  # a shell is always a TUI
    assert list(dialog.variables.GetCheckedItems()) == [1]
    assert dialog.commands.GetStrings() == ["git status"]
    assert dialog.variables.GetString(0) == "Name, {name}"


def test_a_single_command_is_selected_so_edit_and_remove_are_available(
    dialog: ProfileDialog,
) -> None:
    assert dialog.commands.GetCount() == 1
    assert dialog.commands.GetSelection() == 0
    assert dialog.edit_command.IsEnabled()
    assert dialog.remove_command.IsEnabled()


def test_the_buttons_of_the_commands_follow_a_change_of_the_selection(
    dialog: ProfileDialog,
) -> None:
    dialog.commands.SetSelection(wx.NOT_FOUND)
    event = wx.CommandEvent(wx.wxEVT_LISTBOX, dialog.commands.GetId())
    event.SetEventObject(dialog.commands)
    dialog.commands.GetEventHandler().ProcessEvent(event)
    assert not dialog.edit_command.IsEnabled()
    assert not dialog.remove_command.IsEnabled()
    dialog.commands.SetSelection(0)
    dialog.commands.GetEventHandler().ProcessEvent(event)
    assert dialog.edit_command.IsEnabled()


def test_a_profile_without_commands_starts_with_the_buttons_off(app: wx.App) -> None:
    frame = wx.Frame(None)
    box = ProfileDialog(frame, ProfileEditor(Profile("p"), [], lambda text: text))
    try:
        assert box.commands.GetSelection() == wx.NOT_FOUND
        assert not box.edit_command.IsEnabled()
        assert not box.remove_command.IsEnabled()
    finally:
        box.Destroy()
        frame.Destroy()


def test_commit_hands_the_controls_to_the_draft(dialog: ProfileDialog) -> None:
    dialog.name.SetValue("  g2 ")
    dialog.program.SetValue(r"  C:\Tools\git.exe ")
    dialog.prompt_prefix.SetValue("# ")
    dialog.variables.SetCheckedItems([0, 3])
    dialog.terminal_view_only.SetValue(True)
    dialog.commit()
    profile = dialog._editor.build()
    assert (profile.name, profile.variables, profile.terminal_view_only) == (
        "g2",
        ["name", "value1"],
        True,
    )
    assert profile.program == r"C:\Tools\git.exe"
    assert profile.prompt_prefix == "# "


# The menu items ------------------------------------------------------------------------------


@pytest.fixture
def window(app: wx.App, tmp_path: Path) -> Iterator[MainWindow]:
    store = ProfileStore(tmp_path / "profiles")
    store.save(Profile("git", commands=["git status"]))
    frame = MainWindow(
        Settings.load(None),
        FakeLauncher(),
        tmp_path,
        AppContext(profiles_folder=tmp_path / "profiles"),
    )
    frame.Show()
    yield frame
    frame.Close(force=True)


def test_the_variables_dialog_asks_one_field_per_variable(app: wx.App) -> None:
    frame = wx.Frame(None)
    fields = [("source", "Source"), ("value1", "Value 1")]
    with VariablesDialog(frame, "git", fields, {"source": "a.txt"}) as box:
        assert list(box.controls) == ["source", "value1"]
        for variable, label in fields:
            control = box.controls[variable]
            previous = control.GetPrevSibling()
            assert isinstance(previous, wx.StaticText)
            assert previous.GetLabel() == label
            assert control.GetName() == label
        assert box.values() == {"source": "a.txt", "value1": ""}
        box.controls["value1"].SetValue("2")
        assert box.values()["value1"] == "2"
    frame.Destroy()


def answer(window: MainWindow, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The user types ``name`` in the next profile dialog and presses OK."""

    def modal(box: wx.Dialog) -> int:
        assert isinstance(box, ProfileDialog)
        box.name.SetValue(name)
        return int(wx.ID_OK)

    monkeypatch.setattr(window.feedback, "modal", modal)


def item_enabled(window: MainWindow, command: CommandId) -> bool:
    return all(item.IsEnabled() for item in window.menus.items[command])


def test_add_is_always_there_and_edit_needs_a_profile(window: MainWindow) -> None:
    assert item_enabled(window, CommandId.ADD_PROFILE)
    assert not item_enabled(window, CommandId.EDIT_PROFILE)
    window.actions.choose_profile("git")
    assert item_enabled(window, CommandId.EDIT_PROFILE)


def test_add_writes_a_profile_starting_from_the_session(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.set_launch_mode(LaunchMode.TUI)
    answer(window, "new", monkeypatch)
    window.actions.run(CommandId.ADD_PROFILE)
    created = ProfileStore(tmp_path / "profiles").load_all().profiles
    assert [p.name for p in created] == ["git", "new"]
    assert created[1].launch_mode == "tui"
    assert window.actions.current_profile() == "new"  # the profile added is chosen


def test_a_profile_added_under_a_running_program_is_written_but_not_chosen(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.presenter.submit("ping host")
    answer(window, "later", monkeypatch)
    window.actions.run(CommandId.ADD_PROFILE)
    names = [p.name for p in ProfileStore(tmp_path / "profiles").load_all().profiles]
    assert names == ["git", "later"]
    assert window.actions.current_profile() is None


def test_edit_renames_the_profile_and_chooses_it_again(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.actions.choose_profile("git")
    answer(window, "git2", monkeypatch)
    window.actions.run(CommandId.EDIT_PROFILE)
    names = [p.name for p in ProfileStore(tmp_path / "profiles").load_all().profiles]
    assert names == ["git2"]
    assert window.actions.current_profile() == "git2"
    assert window.presenter.profile_values.commands() == ["git status"]


def test_define_variables_is_greyed_unless_the_profile_uses_some(
    window: MainWindow, tmp_path: Path
) -> None:
    ProfileStore(tmp_path / "profiles").save(Profile("var", variables=["name"]))
    window.actions.profile_names()
    assert not item_enabled(window, CommandId.DEFINE_VARIABLES)
    window.actions.choose_profile("git")
    assert not item_enabled(window, CommandId.DEFINE_VARIABLES)
    window.actions.choose_profile("var")
    assert item_enabled(window, CommandId.DEFINE_VARIABLES)


def test_the_values_typed_replace_the_variables_in_the_commands_and_follow_a_rename(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProfileStore(tmp_path / "profiles")
    store.save(Profile("sw", variables=["name"], commands=["git switch {name}"]))
    window.actions.profile_names()
    window.actions.choose_profile("sw")

    def modal(box: wx.Dialog) -> int:
        assert isinstance(box, VariablesDialog)
        box.controls["name"].SetValue("dev")
        return int(wx.ID_OK)

    monkeypatch.setattr(window.feedback, "modal", modal)
    window.actions.run(CommandId.DEFINE_VARIABLES)
    assert window.presenter.profile_values.commands() == ["git switch dev"]

    answer(window, "sw2", monkeypatch)
    window.actions.run(CommandId.EDIT_PROFILE)
    assert window.actions.current_profile() == "sw2"
    assert window.presenter.profile_values.commands() == ["git switch dev"]


def test_the_program_is_greyed_with_a_shell_and_back_without_one(dialog: ProfileDialog) -> None:
    assert not dialog.program.IsEnabled()  # the profile of the dialog has Cmd
    none = [value for value, _name in dialog._interpreters].index("none")
    dialog.interpreter.SetSelection(none)
    dialog._show_mode_state()
    assert dialog.program.IsEnabled()
    assert not dialog.prompt_prefix.IsEnabled()


def test_a_command_added_is_listed_in_order_and_selected(dialog: ProfileDialog) -> None:
    dialog._editor.add_command("a first one")
    dialog._show_commands(0)
    assert dialog.commands.GetStrings() == ["a first one", "git status"]
    assert dialog.commands.GetSelection() == 0


def test_a_shell_has_only_the_shell_type(dialog: ProfileDialog) -> None:
    assert dialog.use.GetStrings() == ["Shell"]
    assert dialog.commands.GetStrings() == ["git status"]


def test_the_type_of_command_filters_the_list_and_add_follows_it(dialog: ProfileDialog) -> None:
    editor = dialog._editor
    dialog.interpreter.SetSelection([value for value, _name in dialog._interpreters].index("none"))
    dialog._show_mode_state()
    assert dialog.use.GetStrings() == ["Launch command", "Program command"]
    assert dialog.commands.GetStrings() == ["git status"]
    editor._lists[CommandUse.PROGRAM] = ["/select"]
    dialog.use.SetSelection(1)
    dialog._show_use()
    assert dialog.commands.GetStrings() == ["/select"]
    assert dialog.commands.GetSelection() == 0
    editor.add_command("/clear")
    dialog._show_commands(0)
    assert dialog.commands.GetStrings() == ["/clear", "/select"]
    dialog.use.SetSelection(0)
    dialog._show_use()
    assert dialog.commands.GetStrings() == ["git status"]
    assert editor.build().program_commands == ["/clear", "/select"]


def test_the_type_label_comes_right_before_its_list(dialog: ProfileDialog) -> None:
    previous = dialog.use.GetPrevSibling()
    assert isinstance(previous, wx.StaticText)
    assert previous.GetLabel() == "Command type"
    assert dialog.use.GetName() == "Command type"


def test_a_command_already_there_is_refused_with_a_message_and_selected(
    dialog: ProfileDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []

    def show_modal(box: wx.MessageDialog) -> int:
        shown.append(box.GetMessage())
        return int(wx.ID_OK)

    monkeypatch.setattr(wx.MessageDialog, "ShowModal", show_modal)
    monkeypatch.setattr(dialog, "_ask_command", lambda title, current: "git status")
    dialog.commands.SetSelection(wx.NOT_FOUND)
    dialog._add_command()
    assert shown == ["This command is already in the list."]
    assert dialog._editor.commands == ["git status"]
    assert dialog.commands.GetSelection() == 0


def test_the_name_is_taken_in_one_spelling_for_accented_letters(dialog: ProfileDialog) -> None:
    dialog.name.SetValue("cafe" + chr(0x301))  # an e and its accent, apart
    dialog.commit()
    assert dialog._editor.name == "caf" + chr(0xE9)
