import pytest

from n5terminal.core.screen.default_output_filter import DefaultOutputFilter
from n5terminal.core.screen.output_filter import (
    CarriageReturnPolicy,
    FilteredChunk,
    FilterRules,
    RemovedAction,
)

pytestmark = pytest.mark.unit


def display(chunks: list[FilteredChunk]) -> str:
    """What an output area shows after applying the chunks."""
    shown = ""
    for chunk in chunks:
        if chunk.replaces_current_line:
            shown = shown[: shown.rfind("\n") + 1] + chunk.text
        else:
            shown += chunk.text
    return shown


def run(*pieces: str, rules: FilterRules | None = None) -> str:
    output_filter = DefaultOutputFilter(rules)
    chunks: list[FilteredChunk] = []
    for piece in pieces:
        chunks += output_filter.feed(piece)
    chunks += output_filter.finish()
    return display(chunks)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("plain text\n", "plain text\n"),
        ("a\tb\n", "a\tb\n"),
        ("\x1b[31mred\x1b[0m\n", "red\n"),
        ("\x1b[?1049h\x1b[2J\x1b[1;1Hscreen", "screen"),
        ("\x1b]0;title\x07after", "after"),
        ("\x1b]0;title\x1b\\after", "after"),
        ("\x1b(Bcharset", "charset"),
        ("\x1b7saved\x1b8", "saved"),
        ("\x9b31mC1\x9d0;t\x9c!", "C1!"),
        ("bell\x07 null\x00 delete\x7f", "bell null delete"),
        ("line\r\nnext\n", "line\nnext\n"),
        ("‮evil‬ ⁦x⁩", "evil x"),
        ("zero​width﻿", "zerowidth"),
        ("decode � error", "decode � error"),
        ("accents é à ç €", "accents é à ç €"),
    ],
)
def test_default_rules(source: str, expected: str) -> None:
    assert run(source) == expected


def test_a_sequence_split_between_two_pieces_is_removed_whole() -> None:
    assert run("before\x1b[3", "1mafter") == "beforeafter"
    assert run("before\x1b", "]0;title", "\x07after") == "beforeafter"


def test_a_carriage_return_split_from_its_line_feed_is_one_line_break() -> None:
    assert run("one\r", "\ntwo") == "one\ntwo"


def test_progress_bar_keeps_only_the_last_state_of_the_line() -> None:
    assert run("start\n10%", "\r50%", "\r100%\n", "end") == "start\n100%\nend"


def test_carriage_return_overwrites_like_a_terminal() -> None:
    assert run("abcdef\rxy") == "xycdef"


def test_rewritten_line_is_handed_out_as_a_replacement() -> None:
    output_filter = DefaultOutputFilter()
    assert output_filter.feed("10%") == [FilteredChunk("10%")]
    assert output_filter.feed("\r20%") == [FilteredChunk("20%", replaces_current_line=True)]
    assert output_filter.feed(" done\n") == [FilteredChunk(" done\n")]


def test_appending_after_a_carriage_return_is_not_a_replacement() -> None:
    output_filter = DefaultOutputFilter()
    output_filter.feed("abc\r")
    assert output_filter.feed("abcdef") == [FilteredChunk("def")]


def test_new_line_policy() -> None:
    rules = FilterRules(carriage_return=CarriageReturnPolicy.NEW_LINE)
    assert run("10%\r50%\r100%", rules=rules) == "10%\n50%\n100%"


def test_mark_policy_puts_one_mark_per_removed_item() -> None:
    rules = FilterRules(on_removed=RemovedAction.MARK, mark="?")
    assert run("a\x1b[31mb\x07c", rules=rules) == "a?b?c"


def test_switches_can_keep_what_is_removed_by_default() -> None:
    rules = FilterRules(strip_direction_marks=False, strip_zero_width=False)
    assert run("‮x​", rules=rules) == "‮x​"


def test_unfinished_sequence_at_the_end_is_dropped() -> None:
    assert run("text\x1b[31") == "text"


def test_too_long_unfinished_sequence_is_dropped() -> None:
    output_filter = DefaultOutputFilter()
    chunks = output_filter.feed("a\x1b]" + "x" * 5000)
    chunks += output_filter.feed("b")
    assert display(chunks) == "ab"
