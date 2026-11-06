import pytest

from n5terminal.core.config.keys import KEY_GROUPS, SENT_KEYS, key_named
from n5terminal.core.config.shortcuts import (
    CONFIGURABLE_COMMANDS,
    KEY_COMMANDS,
    KEYS_GROUP,
    MAIN_GROUP,
)

pytestmark = pytest.mark.unit


def test_the_ids_and_the_bytes_are_unique() -> None:
    assert len({key.id for key in SENT_KEYS}) == len(SENT_KEYS)
    assert len({key.data for key in SENT_KEYS}) == len(SENT_KEYS)


def test_every_key_is_in_a_group_and_every_group_is_shown() -> None:
    assert [key for _group, keys in KEY_GROUPS for key in keys] == list(SENT_KEYS)


def test_a_cursor_key_has_the_form_the_program_asked_for() -> None:
    up = key_named("up")
    assert up is not None
    assert up.bytes_for(False) == b"\x1b[A"
    assert up.bytes_for(True) == b"\x1bOA"


def test_the_other_keys_do_not_depend_on_the_mode() -> None:
    escape = key_named("escape")
    page_up = key_named("page_up")
    assert escape is not None
    assert page_up is not None
    assert escape.bytes_for(True) == escape.bytes_for(False) == b"\x1b"
    assert page_up.bytes_for(True) == b"\x1b[5~"


def test_enter_is_a_carriage_return_like_a_terminal_keyboard() -> None:
    enter = key_named("enter")
    assert enter is not None
    assert enter.data == b"\r"


def test_each_key_is_a_command_and_only_escape_and_enter_have_a_shortcut() -> None:
    assert len(KEY_COMMANDS) == len(SENT_KEYS)
    defaults = {command.id: command.default for command in KEY_COMMANDS if command.default}
    assert defaults == {"key.escape": "Shift+Esc", "key.enter": "Shift+Enter"}
    assert {command.group for command in KEY_COMMANDS} == {KEYS_GROUP}
    assert all(command in CONFIGURABLE_COMMANDS for command in KEY_COMMANDS)
    assert any(command.group == MAIN_GROUP for command in CONFIGURABLE_COMMANDS)


def test_the_text_of_a_key_command_says_send_then_the_key() -> None:
    escape = next(command for command in KEY_COMMANDS if command.id == "key.escape")
    assert escape.text(lambda message: message) == "Send Escape"
