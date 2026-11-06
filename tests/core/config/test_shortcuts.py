import pytest

from n5terminal.core.config.shortcuts import (
    _KEY_NAMES,
    _NAMED_KEYS,
    CHOOSE_FOLDER_COMMAND,
    CONFIGURABLE_COMMANDS,
    FIXED_SHORTCUTS,
    HISTORY_COMMAND,
    NEW_SESSION_COMMAND,
    STOP_COMMAND,
    ShortcutProblem,
    check_shortcut,
    display_shortcut,
    normalize_shortcut,
)
from n5terminal.i18n import _, install

pytestmark = pytest.mark.unit

DEFAULTS = {command.id: command.default for command in CONFIGURABLE_COMMANDS}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ctrl + shift + o", "Ctrl+Shift+O"),
        ("shift+ctrl+o", "Ctrl+Shift+O"),
        ("f2", "F2"),
        ("alt+down", "Alt+Down"),
        ("ctrl+pause", "Ctrl+Pause"),
        ("ctrl+space", "Ctrl+Space"),
        ("", ""),
        ("Ctrl+", None),
        ("Ctrl+Ctrl+O", None),
        ("Hyper+O", None),
        ("Ctrl+F13", None),
    ],
)
def test_normalize_shortcut(text: str, expected: str | None) -> None:
    assert normalize_shortcut(text) == expected


def test_the_defaults_are_valid_and_do_not_collide() -> None:
    shortcuts = [command.default for command in CONFIGURABLE_COMMANDS if command.default]
    assert len(set(shortcuts)) == len(shortcuts)  # the commands with no shortcut are all ""
    for command in CONFIGURABLE_COMMANDS:
        assert check_shortcut(command, command.default, DEFAULTS).problem is None


def test_ctrl_c_stays_copy_and_stopping_has_its_own_shortcut() -> None:
    assert "Ctrl+C" in FIXED_SHORTCUTS
    assert STOP_COMMAND.default == "Ctrl+Pause"
    assert HISTORY_COMMAND.default == "Ctrl+Space"


def test_a_free_shortcut_is_accepted() -> None:
    assert check_shortcut(STOP_COMMAND, "Ctrl+K", DEFAULTS).problem is None


def test_no_shortcut_is_accepted() -> None:
    assert check_shortcut(STOP_COMMAND, "", DEFAULTS).problem is None


def test_a_plain_letter_is_refused() -> None:
    assert check_shortcut(STOP_COMMAND, "K", DEFAULTS).problem is ShortcutProblem.RESERVED


def test_a_plain_enter_is_refused() -> None:
    assert check_shortcut(STOP_COMMAND, "Enter", DEFAULTS).problem is ShortcutProblem.RESERVED


def test_enter_with_a_modifier_is_accepted() -> None:
    assert check_shortcut(STOP_COMMAND, "Alt+Enter", DEFAULTS).problem is None


@pytest.mark.parametrize("key", ["Tab", "Esc", "Insert"])
def test_navigation_keys_are_refused(key: str) -> None:
    check = check_shortcut(STOP_COMMAND, f"Ctrl+{key}", DEFAULTS)
    assert check.problem in (ShortcutProblem.RESERVED, ShortcutProblem.FIXED)


@pytest.mark.parametrize("shortcut", ["Ctrl+Q", "Ctrl+C", "Alt+F", "Alt+S", "Alt+D"])
def test_a_standard_shortcut_is_refused(shortcut: str) -> None:
    assert check_shortcut(STOP_COMMAND, shortcut, DEFAULTS).problem is ShortcutProblem.FIXED


def test_a_shortcut_of_another_command_is_refused() -> None:
    check = check_shortcut(STOP_COMMAND, "Ctrl+N", DEFAULTS)
    assert check.problem is ShortcutProblem.TAKEN
    assert check.other == NEW_SESSION_COMMAND


def test_keeping_its_own_shortcut_is_accepted() -> None:
    assert check_shortcut(CHOOSE_FOLDER_COMMAND, "Ctrl+O", DEFAULTS).problem is None


@pytest.mark.parametrize(
    ("shortcut", "shown"),
    [
        ("Alt+Home", "Alt+Début"),
        ("Alt+End", "Alt+Fin"),
        ("Ctrl+Pause", "Ctrl+Pause"),
        ("Shift+Esc", "Maj+Échap"),
        ("Ctrl+Shift+PageDown", "Ctrl+Maj+Page suivante"),
        ("Ctrl+Space", "Ctrl+Espace"),
        ("F4", "F4"),
        ("Ctrl+G", "Ctrl+G"),
        ("", ""),
    ],
)
def test_the_keys_are_shown_by_their_french_names(shortcut: str, shown: str) -> None:
    """A French voice reads "Home" as "dossier personnel": the names are shown in French."""
    install("fr")
    try:
        assert display_shortcut(shortcut, _) == shown
    finally:
        install("en")


def test_in_english_the_names_are_the_stored_ones() -> None:
    assert display_shortcut("Ctrl+Shift+PageDown", _) == "Ctrl+Shift+PageDown"


def test_every_named_key_of_the_rules_has_a_name_to_show() -> None:
    assert set(_NAMED_KEYS) <= set(_KEY_NAMES)
