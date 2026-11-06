import pytest

from n5terminal.core.config.profiles import CommandUse
from n5terminal.core.session.command_history import CommandHistory

pytestmark = pytest.mark.unit


def history(*commands: str, limit: int = 100) -> CommandHistory:
    result = CommandHistory(limit)
    for command in commands:
        result.add(command)
    return result


def test_commands_are_kept_in_order() -> None:
    assert history("a", "b", "c").items() == ("a", "b", "c")


def test_blank_commands_are_not_kept_and_a_repeat_replaces_the_older_one() -> None:
    assert history("a", "", "  ", "a", "b", "a").items() == ("b", "a")
    assert history("dir", "cd", "dir").items() == ("cd", "dir")


def test_a_repeat_does_not_use_up_the_limit() -> None:
    assert history("a", "b", "a", "b", "c", limit=3).items() == ("a", "b", "c")


def test_the_oldest_commands_are_dropped_past_the_limit() -> None:
    assert history("a", "b", "c", limit=2).items() == ("b", "c")


def test_the_commands_are_listed_by_use() -> None:
    result = CommandHistory()
    result.add("git push")  # launched
    result.add("dir", CommandUse.PROGRAM)  # typed in a shell
    result.add("cd ..", CommandUse.PROGRAM)
    assert result.items() == ("git push", "dir", "cd ..")
    assert result.items_of(CommandUse.LAUNCH) == ("git push",)
    assert result.items_of(CommandUse.PROGRAM) == ("dir", "cd ..")


def test_the_same_text_with_another_use_is_kept() -> None:
    result = CommandHistory()
    result.add("exit")
    result.add("exit", CommandUse.PROGRAM)
    assert result.items() == ("exit", "exit")
    result.add("exit")  # the older launch "exit" goes, not the program one
    assert result.items_of(CommandUse.PROGRAM) == ("exit",)
    assert result.items() == ("exit", "exit")
