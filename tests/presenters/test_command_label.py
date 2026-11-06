"""How a block is normalized and read in the list of commands."""

import pytest

from n5terminal.presenters.command_label import MAX_LABEL, command_label, is_block, normalize_block

pytestmark = pytest.mark.unit


def same(text: str) -> str:
    return text


def test_a_single_line_is_left_as_it_is() -> None:
    assert normalize_block("dir") == "dir"
    assert normalize_block("  dir  ") == "  dir  "
    assert command_label("x" * 200, same) == "x" * 200
    assert not is_block("dir")


def test_line_breaks_are_normalized_and_the_empty_lines_at_the_end_dropped() -> None:
    assert normalize_block("a\r\nb\rc\n\n\n") == "a\nb\nc"
    assert is_block(normalize_block("a\r\nb"))


def test_a_block_reads_as_its_first_line_and_its_number_of_lines() -> None:
    assert command_label("one\ntwo\nthree", same) == "one (3 lines)"


def test_a_long_first_line_is_cut_with_an_ellipsis() -> None:
    label = command_label("x" * 80 + "\nnext", same)
    assert label == "x" * MAX_LABEL + "… (2 lines)"
