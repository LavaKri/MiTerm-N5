"""Light checks of the Preferences dialog: names, choices shown, what it hands to the settings."""

from collections.abc import Iterator

import pytest
import wx

from n5terminal.core.config.announcements import CATEGORIES
from n5terminal.core.config.screen_reader import NONE
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    KEY_COMMANDS,
    MAIN_GROUP,
    STOP_COMMAND,
)
from n5terminal.presenters.general_preferences import MAX_OUTPUT_LIMIT, MIN_OUTPUT_LIMIT
from n5terminal.ui.preferences_dialog import PreferencesDialog

pytestmark = pytest.mark.ui


@pytest.fixture
def frame(app: wx.App) -> Iterator[wx.Frame]:
    window = wx.Frame(None)
    yield window
    window.Destroy()
    wx.Yield()  # wx destroys a top-level window later: let it do it before the next test


def make(frame: wx.Frame, settings: Settings) -> PreferencesDialog:
    return PreferencesDialog(frame, settings)


def fire(control: wx.Control, event_type: int) -> None:
    """What the user does with a control: the event it would send."""
    event = wx.CommandEvent(event_type, control.GetId())
    event.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(event)


# The dialog ------------------------------------------------------------------------------------


def test_it_opens_on_the_general_tab_with_the_focus_on_the_tabs(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        assert dialog.notebook.GetSelection() == 0
        assert dialog.notebook.GetPageText(0) == "General"
        assert [dialog.notebook.GetPageText(i) for i in range(3)] == [
            "General",
            "Shortcuts",
            "Announcements",
        ]
        assert dialog.notebook.GetPageCount() == 3


def test_the_startup_profile_label_comes_right_before_its_list(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        control = dialog.general_page.startup_profile
        previous = control.GetPrevSibling()
        assert isinstance(previous, wx.StaticText)
        assert previous.GetLabel() == "Startup profile"
        assert control.GetName() == "Startup profile"


def test_the_startup_profile_is_chosen_among_the_free_profile_and_the_profiles(
    frame: wx.Frame,
) -> None:
    settings = Settings(startup_profile="npm")
    with PreferencesDialog(frame, settings, None, ["git", "npm"]) as dialog:
        page = dialog.general_page
        assert page.startup_profile.GetStrings() == ["Free", "git", "npm"]
        assert page.startup_profile.GetStringSelection() == "npm"
        page.startup_profile.SetStringSelection("git")
        dialog.commit()
    assert settings.startup_profile == "git"
    with PreferencesDialog(frame, settings, None, ["git"]) as dialog:
        dialog.general_page.startup_profile.SetSelection(0)
        dialog.commit()
    assert settings.startup_profile == ""


def test_a_startup_profile_that_is_gone_shows_as_free_and_is_kept_unless_chosen_again(
    frame: wx.Frame,
) -> None:
    settings = Settings(startup_profile="gone")
    with PreferencesDialog(frame, settings, None, ["git"]) as dialog:
        assert dialog.general_page.startup_profile.GetSelection() == 0
        dialog.commit()
    assert settings.startup_profile == "gone"


def test_nothing_changed_gives_no_change(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        assert not dialog.commit().any


# General ---------------------------------------------------------------------------------------


def test_the_controls_show_the_settings(frame: wx.Frame) -> None:
    settings = Settings(language="en", output_limit=5_000)
    with make(frame, settings) as dialog:
        page = dialog.general_page
        assert page.language.GetStringSelection() == "English"
        assert page.limit.GetValue() == 5_000


def test_every_control_of_the_general_page_has_an_accessible_name(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        assert dialog.general_page.language.GetName()
        assert dialog.general_page.limit.GetName()


def test_the_languages_are_written_in_their_own_language(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        names = [dialog.general_page.language.GetString(i) for i in range(2)]
        assert names == ["Français", "English"]


def test_the_size_of_the_output_is_limited_by_the_control(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.general_page
        assert (page.limit.GetMin(), page.limit.GetMax()) == (MIN_OUTPUT_LIMIT, MAX_OUTPUT_LIMIT)


def test_what_the_general_controls_show_goes_to_the_settings(frame: wx.Frame) -> None:
    settings = Settings()
    with make(frame, settings) as dialog:
        dialog.general_page.language.SetSelection(1)
        dialog.general_page.limit.SetValue(2_000)
        changes = dialog.commit()
    assert changes.language
    assert changes.output_limit
    assert not changes.screen_reader_output
    assert (settings.language, settings.output_limit) == ("en", 2_000)


# Announcements ---------------------------------------------------------------------------------


def test_the_output_of_the_announcements_is_at_the_top_of_its_page(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.announcements_page
        assert page.output.GetName() == "Announcement output"
        assert page.output.GetCount() >= 1
        top = page.output.GetPosition().y
        assert top < page.categories.GetPosition().y


def test_choosing_another_output_is_handed_to_the_settings(frame: wx.Frame) -> None:
    settings = Settings(screen_reader_output="uia")
    with make(frame, settings) as dialog:
        page = dialog.announcements_page
        page.output.SetSelection(page.output.FindString("No output"))
        changes = dialog.commit()
    assert changes.screen_reader_output
    assert settings.screen_reader_output == NONE.id


def test_the_announcements_page_lists_one_line_per_category(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.announcements_page
        assert page.categories.GetCount() == len(CATEGORIES)
        assert page.categories.GetName()
        assert page.destination.GetName()
        assert ", " in page.categories.GetString(0)  # the category, then its destination


def test_the_destinations_offered_are_those_the_category_accepts(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.announcements_page
        accepted = {len(c.choices) for c in CATEGORIES}
        assert page.destination.GetCount() in accepted
        assert page.destination.GetSelection() != wx.NOT_FOUND


def test_choosing_a_destination_changes_the_line_and_the_settings(frame: wx.Frame) -> None:
    settings = Settings()
    with make(frame, settings) as dialog:
        page = dialog.announcements_page
        page.categories.SetSelection(0)
        fire(page.categories, wx.wxEVT_LISTBOX)
        before = page.categories.GetString(0)
        page.destination.SetSelection(0)  # "no announcement" comes first for every category
        fire(page.destination, wx.wxEVT_CHOICE)
        assert page.categories.GetString(0) != before
        changes = dialog.commit()
    assert changes.announcements
    assert settings.announcements


# Shortcuts -------------------------------------------------------------------------------------


def select(dialog: PreferencesDialog, command_id: str) -> None:
    index = [command.id for command in CONFIGURABLE_COMMANDS].index(command_id)
    dialog.shortcuts_page.command_list.SetSelection(index)
    fire(dialog.shortcuts_page.command_list, wx.wxEVT_LISTBOX)


def test_the_shortcuts_page_lists_one_line_per_command(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.shortcuts_page
        main = [command for command in CONFIGURABLE_COMMANDS if command.group == MAIN_GROUP]
        assert page.command_list.GetCount() == len(main)
        assert page.command_list.GetName()
        assert page.capture.GetName()
        assert ", " in page.command_list.GetString(0)  # the command, then its shortcut


def test_the_choice_of_group_shows_the_keys_sent(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.shortcuts_page
        assert page.group_choice.GetCount() == 2
        page.group_choice.SetSelection(1)
        fire(page.group_choice, wx.wxEVT_CHOICE)
        assert page.command_list.GetCount() == len(KEY_COMMANDS)
        assert page.selected_command() == KEY_COMMANDS[0]
        assert page.capture.GetValue()  # "none", not empty


def test_the_field_shows_the_shortcut_of_the_selected_command(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        select(dialog, STOP_COMMAND.id)
        assert dialog.shortcuts_page.capture.GetValue() == "Ctrl+Pause"


def test_a_shortcut_pressed_is_given_to_the_command(frame: wx.Frame) -> None:
    settings = Settings()
    with make(frame, settings) as dialog:
        select(dialog, STOP_COMMAND.id)
        dialog.shortcuts_page.assign_pressed("Ctrl+K")
        assert dialog.shortcuts_page.capture.GetValue() == "Ctrl+K"
        assert "Ctrl+K" in dialog.shortcuts_page.command_list.GetString(
            dialog.shortcuts_page.command_list.GetSelection()
        )
        changes = dialog.commit()
    assert changes.shortcuts
    assert settings.shortcut_for(STOP_COMMAND) == "Ctrl+K"


def test_the_buttons_restore_the_default_and_remove_the_shortcut(frame: wx.Frame) -> None:
    with make(frame, Settings()) as dialog:
        page = dialog.shortcuts_page
        select(dialog, STOP_COMMAND.id)
        page.clear_shortcut()
        assert page.capture.GetValue() == "none"
        page.restore_default()
        assert page.capture.GetValue() == "Ctrl+Pause"


def test_the_general_page_has_the_association_button_named_after_what_it_does(
    frame: wx.Frame,
) -> None:
    with make(frame, Settings()) as dialog:
        button = dialog.general_page.association
        assert button.GetLabel() == "Associate the .n5term files with MiTerm-N5"
        assert button.AcceptsFocusFromKeyboard()
