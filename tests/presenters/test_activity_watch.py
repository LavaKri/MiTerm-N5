import pytest

from n5terminal.presenters.activity_watch import ECHO_GRACE, ActivityWatch

pytestmark = pytest.mark.unit


def test_nothing_changed_nothing_to_signal() -> None:
    watch = ActivityWatch()
    assert not watch.check(5.0, 1.0)


def test_a_change_is_seen_at_the_next_check_and_only_once() -> None:
    watch = ActivityWatch()
    watch.note(0.2)
    assert watch.check(1.0, 1.0)
    assert not watch.check(2.0, 1.0)  # the flag was lowered by the check


def test_the_flag_is_looked_at_once_per_interval() -> None:
    watch = ActivityWatch()
    watch.note(0.1)
    assert not watch.check(0.9, 1.0)  # too soon: the flag stays up
    assert watch.check(1.0, 1.0)
    watch.note(1.1)
    assert not watch.check(1.9, 1.0)
    assert watch.check(2.0, 1.0)


def test_a_longer_interval_waits_longer() -> None:
    watch = ActivityWatch()
    watch.note(0.0)
    assert not watch.check(4.9, 5.0)
    assert watch.check(5.0, 5.0)


def test_a_new_program_forgets_the_changes_and_counts_from_now() -> None:
    watch = ActivityWatch()
    watch.note(0.5)
    watch.reset(10.0)
    assert not watch.check(10.5, 1.0)
    watch.note(10.6)
    assert watch.check(11.0, 1.0)


def test_what_a_program_echoes_just_after_something_was_sent_is_no_activity() -> None:
    watch = ActivityWatch()
    watch.sent(1.0)
    watch.note(1.0 + ECHO_GRACE / 2)
    assert not watch.check(3.0, 1.0)
    watch.note(1.0 + ECHO_GRACE)
    assert watch.check(5.0, 1.0)
