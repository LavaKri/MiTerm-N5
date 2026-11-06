import pytest

from n5terminal.core.screen.terminal_size import (
    DEFAULT_SIZE,
    STANDARD_SIZES,
    AutoSizePolicy,
    SizeChoice,
    TerminalSize,
)

pytestmark = pytest.mark.unit


def test_default_size_is_120_by_30_like_windows_terminal() -> None:
    assert AutoSizePolicy().size == DEFAULT_SIZE
    assert (DEFAULT_SIZE.columns, DEFAULT_SIZE.rows) == (120, 30)
    assert DEFAULT_SIZE in STANDARD_SIZES


def test_nothing_to_report_keeps_the_size() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([]) is None
    assert policy.size == DEFAULT_SIZE


def test_one_or_two_characters_too_many_do_not_make_it_grow() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([1, 2, 1, 2, 2]) is None


def test_more_than_two_characters_seen_twice_make_it_grow() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([3]) is None
    assert policy.observe([5]) == TerminalSize(132, 43)
    assert policy.size == TerminalSize(132, 43)


def test_two_long_lines_in_the_same_call_make_it_grow_once() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([3, 4]) == TerminalSize(132, 43)


def test_more_than_ten_characters_once_make_it_grow() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([11]) == TerminalSize(132, 43)


def test_ten_characters_once_do_not() -> None:
    policy = AutoSizePolicy()
    assert policy.observe([10]) is None


def test_it_grows_one_standard_size_at_a_time() -> None:
    policy = AutoSizePolicy()
    wider = STANDARD_SIZES[STANDARD_SIZES.index(DEFAULT_SIZE) + 1 :]
    sizes = [policy.observe([500]) for _ in wider]
    assert sizes == list(wider)


def test_it_never_goes_past_the_largest_size() -> None:
    policy = AutoSizePolicy(STANDARD_SIZES[-1])
    assert policy.observe([500]) is None
    assert policy.size == STANDARD_SIZES[-1]


def test_growing_forgets_the_small_excesses_seen_before() -> None:
    policy = AutoSizePolicy()
    policy.observe([3])
    policy.observe([11])
    assert policy.observe([3]) is None


def test_a_size_that_is_not_standard_grows_to_the_next_wider_one() -> None:
    policy = AutoSizePolicy(TerminalSize(90, 40))
    assert policy.observe([20]) == TerminalSize(100, 30)


def test_the_choice_starts_automatic_at_120_by_30() -> None:
    choice = SizeChoice()
    assert choice.size == DEFAULT_SIZE
    assert choice.observe([500]) == TerminalSize(132, 43)
    assert choice.size == TerminalSize(132, 43)


def test_a_chosen_size_is_kept_and_never_grows() -> None:
    choice = SizeChoice()
    choice.choose(TerminalSize(80, 24), DEFAULT_SIZE)
    assert choice.size == TerminalSize(80, 24)
    assert choice.observe([500]) is None
    assert choice.size == TerminalSize(80, 24)


def test_going_back_to_automatic_goes_on_from_the_current_size() -> None:
    choice = SizeChoice()
    choice.choose(TerminalSize(80, 24), DEFAULT_SIZE)
    choice.choose(None, TerminalSize(80, 24))
    assert choice.size == TerminalSize(80, 24)
    assert choice.observe([500]) == TerminalSize(100, 30)
