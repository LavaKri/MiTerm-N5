import pytest

from n5terminal.core.config.settings import Settings
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    FIND_COMMAND,
    KEY_COMMANDS,
    KEYS_GROUP,
    MAIN_GROUP,
    NEW_SESSION_COMMAND,
    STOP_COMMAND,
    ShortcutProblem,
)
from n5terminal.presenters.preferences_changes import AppliedChanges
from n5terminal.presenters.shortcuts_preferences import ShortcutsPreferences

pytestmark = pytest.mark.unit

FRENCH = {
    "Stop the program": "Arrêter le programme",
    "New session": "Nouvelle session",
    "none": "aucun",
}


def translate(text: str) -> str:
    return FRENCH.get(text, text)


def page(settings: Settings | None = None) -> ShortcutsPreferences:
    return ShortcutsPreferences(settings or Settings(), translate)


def test_there_is_one_line_per_configurable_command_saying_the_command_then_its_shortcut() -> None:
    preferences = page()
    main = preferences.commands()
    assert main == [command for command in CONFIGURABLE_COMMANDS if command.group == MAIN_GROUP]
    assert preferences.line(STOP_COMMAND) == "Arrêter le programme, Ctrl+Pause"


def test_the_keys_sent_are_a_group_of_their_own_with_no_shortcut() -> None:
    preferences = page()
    assert preferences.groups() == [MAIN_GROUP, KEYS_GROUP]
    keys = preferences.commands(KEYS_GROUP)
    assert keys == list(KEY_COMMANDS)
    assert preferences.line(keys[0]) == "Send Up arrow, aucun"
    escape = next(command for command in keys if command.id == "key.escape")
    assert preferences.line(escape) == "Send Escape, Shift+Esc"
    assert len(preferences.commands()) + len(keys) == len(CONFIGURABLE_COMMANDS)


def test_a_key_shortcut_follows_the_same_rules() -> None:
    preferences = page()
    escape = next(command for command in KEY_COMMANDS if command.id == "key.escape")
    assert preferences.assign(escape, "Esc").problem is ShortcutProblem.RESERVED
    assert preferences.assign(escape, "Ctrl+Esc").problem is ShortcutProblem.RESERVED
    assert preferences.assign(escape, "Shift+Esc").problem is None
    assert preferences.assign(escape, "Ctrl+C").problem is ShortcutProblem.FIXED
    assert preferences.assign(escape, "Ctrl+K").problem is None
    message = preferences.problem_message(preferences.assign(STOP_COMMAND, "Ctrl+K"), "Ctrl+K")
    assert "Send Escape" in message


def test_a_command_without_shortcut_says_none() -> None:
    settings = Settings()
    settings.set_shortcut(STOP_COMMAND, "")
    assert page(settings).line(STOP_COMMAND) == "Arrêter le programme, aucun"


def test_a_valid_shortcut_is_given() -> None:
    preferences = page()
    assert preferences.assign(STOP_COMMAND, "Ctrl+K").problem is None
    assert preferences.shortcut(STOP_COMMAND) == "Ctrl+K"


@pytest.mark.parametrize(
    ("shortcut", "problem"),
    [
        ("Ctrl+R", ShortcutProblem.TAKEN),  # the one of "run again"
        ("Ctrl+Q", ShortcutProblem.FIXED),
        ("Tab", ShortcutProblem.RESERVED),
        ("K", ShortcutProblem.RESERVED),  # a plain letter would block typing
        ("Ctrl+", ShortcutProblem.INVALID),
    ],
)
def test_a_refused_shortcut_is_not_given_and_the_reason_is_known(
    shortcut: str, problem: ShortcutProblem
) -> None:
    preferences = page()
    before = preferences.shortcut(STOP_COMMAND)
    check = preferences.assign(STOP_COMMAND, shortcut)
    assert check.problem is problem
    assert preferences.shortcut(STOP_COMMAND) == before


def test_the_message_names_the_command_that_already_has_the_shortcut() -> None:
    preferences = page()
    check = preferences.assign(NEW_SESSION_COMMAND, "Ctrl+Pause")
    message = preferences.problem_message(check, "Ctrl+Pause")
    assert "Ctrl+Pause" in message
    assert "Arrêter le programme" in message


def test_every_problem_has_a_message_with_the_shortcut() -> None:
    preferences = page()
    for shortcut in ("Ctrl+Q", "Tab", "Ctrl+"):
        check = preferences.assign(STOP_COMMAND, shortcut)
        assert shortcut in preferences.problem_message(check, shortcut)


def test_restoring_the_default_and_clearing() -> None:
    preferences = page()
    preferences.assign(FIND_COMMAND, "Ctrl+K")
    assert preferences.restore_default(FIND_COMMAND).problem is None
    assert preferences.shortcut(FIND_COMMAND) == FIND_COMMAND.default
    assert preferences.clear(FIND_COMMAND).problem is None
    assert preferences.shortcut(FIND_COMMAND) == ""


def test_restoring_a_default_that_another_command_took_is_refused() -> None:
    preferences = page()
    preferences.assign(NEW_SESSION_COMMAND, "Ctrl+K")
    preferences.assign(STOP_COMMAND, NEW_SESSION_COMMAND.default)  # takes Ctrl+N
    check = preferences.restore_default(NEW_SESSION_COMMAND)
    assert check.problem is ShortcutProblem.TAKEN
    assert preferences.shortcut(NEW_SESSION_COMMAND) == "Ctrl+K"


def test_nothing_changed_says_so() -> None:
    assert page().apply() == AppliedChanges()


def test_apply_stores_only_the_differences_from_the_defaults() -> None:
    settings = Settings()
    preferences = page(settings)
    preferences.assign(STOP_COMMAND, "Ctrl+K")
    assert preferences.apply() == AppliedChanges(shortcuts=True)
    assert settings.shortcuts == {STOP_COMMAND.id: "Ctrl+K"}
    preferences.restore_default(STOP_COMMAND)
    assert preferences.apply().shortcuts
    assert settings.shortcuts == {}
