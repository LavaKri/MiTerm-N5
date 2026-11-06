import pytest

from n5terminal.core.screen.output_filter import (
    DEFAULT_KEPT,
    CarriageReturnPolicy,
    FilteredChunk,
    FilterRules,
    RemovedAction,
)

pytestmark = pytest.mark.unit


def test_default_rules_follow_the_documented_policy() -> None:
    rules = FilterRules()
    assert rules.kept == DEFAULT_KEPT == frozenset({"\t", "\n"})
    assert rules.carriage_return is CarriageReturnPolicy.REPLACE_LINE
    assert rules.on_removed is RemovedAction.DROP
    assert rules.strip_escape_sequences
    assert rules.strip_c1_controls
    assert rules.strip_direction_marks
    assert rules.strip_zero_width


def test_rules_can_be_changed_without_touching_the_others() -> None:
    rules = FilterRules(carriage_return=CarriageReturnPolicy.NEW_LINE)
    assert rules.carriage_return is CarriageReturnPolicy.NEW_LINE
    assert rules.kept == DEFAULT_KEPT


def test_chunk_appends_by_default() -> None:
    assert not FilteredChunk("text").replaces_current_line
