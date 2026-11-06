"""The foreground is only taken back from a console window of this very process."""

import logging
import threading

import pytest

from fakes.fake_foreground import FakeForeground
from n5terminal.core.transport.foreground import (
    ATTEMPTS,
    ForegroundWatch,
    Holder,
    Win32Foreground,
    classify,
    hold_foreground,
)

pytestmark = pytest.mark.unit

WINDOW = 4242
TAKE_BACK = f"take_back {WINDOW}"


def watch_in_the_main_window(windows: FakeForeground) -> ForegroundWatch:
    """A watch that saw the main window hold the foreground; the next look sees the holder
    ``windows`` has now."""
    then = windows.current
    windows.current = Holder.OWN_WINDOW
    watch = ForegroundWatch(windows)
    assert not watch.check(WINDOW)
    windows.current = then  # the foreground changes between two looks
    return watch


@pytest.mark.parametrize("name", ["ConsoleWindowClass", "PseudoConsoleWindow"])
def test_a_console_window_of_this_process_is_recognised(name: str) -> None:
    assert classify(name, 10, 10) is Holder.OWN_CONSOLE


def test_a_console_window_of_another_process_is_left_alone() -> None:
    # Windows Terminal and other applications own such windows too.
    assert classify("PseudoConsoleWindow", 11, 10) is Holder.OTHER
    assert classify("ConsoleWindowClass", 11, 10) is Holder.OTHER


def test_another_window_of_this_process_is_one_of_ours() -> None:
    assert classify("wxWindowNR", 10, 10) is Holder.OWN_WINDOW
    assert classify("#32770", 10, 10) is Holder.OWN_WINDOW


def test_the_foreground_of_the_tests_is_not_a_console_window_of_this_process() -> None:
    assert Win32Foreground().holder() is not Holder.OWN_CONSOLE


def test_nothing_is_done_while_the_main_window_keeps_the_foreground() -> None:
    windows = FakeForeground(Holder.OWN_WINDOW)
    watch = ForegroundWatch(windows)
    assert not watch.check(WINDOW)
    assert not watch.check(WINDOW)
    assert windows.calls == []


def test_nothing_is_done_when_the_main_window_never_had_the_foreground() -> None:
    windows = FakeForeground(Holder.OWN_CONSOLE)
    assert not ForegroundWatch(windows).check(WINDOW)
    assert windows.calls == []


def test_the_foreground_is_taken_back_from_the_console_window() -> None:
    windows = FakeForeground(Holder.OWN_CONSOLE)
    watch = watch_in_the_main_window(windows)
    assert watch.check(WINDOW)
    # A lock that still stands would refuse the call: it is lifted first.
    assert windows.calls == ["unlock", TAKE_BACK]


def test_a_switch_to_another_application_is_never_touched() -> None:
    windows = FakeForeground(Holder.OTHER)
    watch = watch_in_the_main_window(windows)
    assert not watch.check(WINDOW)
    assert not watch.check(WINDOW)
    assert windows.calls == []


def test_a_refused_call_is_tried_again_at_the_next_looks() -> None:
    windows = FakeForeground(Holder.OWN_CONSOLE, take_back_results=(False, False, True))
    watch = watch_in_the_main_window(windows)
    assert not watch.check(WINDOW)
    assert not watch.check(WINDOW)
    assert watch.check(WINDOW)
    assert not watch.check(WINDOW)  # taken back: nothing more to do
    assert windows.calls.count(TAKE_BACK) == 3


def test_the_attempts_stop_when_the_user_goes_to_another_application() -> None:
    windows = FakeForeground(Holder.OWN_CONSOLE, take_back_results=(False,))
    watch = watch_in_the_main_window(windows)
    assert not watch.check(WINDOW)
    windows.current = Holder.OTHER  # Alt+Tab to a browser
    assert not watch.check(WINDOW)
    windows.current = Holder.OWN_CONSOLE  # the console comes back: the claim is over
    assert not watch.check(WINDOW)
    assert windows.calls.count(TAKE_BACK) == 1


def test_it_gives_up_after_the_attempts_and_logs_who_holds_the_foreground(
    caplog: pytest.LogCaptureFixture,
) -> None:
    windows = FakeForeground(Holder.OWN_CONSOLE, take_back_results=(False,) * (ATTEMPTS + 5))
    watch = watch_in_the_main_window(windows)
    with caplog.at_level(logging.WARNING):
        for _ in range(ATTEMPTS + 5):
            assert not watch.check(WINDOW)
    assert windows.calls.count(TAKE_BACK) == ATTEMPTS
    assert "held by a fake window" in caplog.text


def test_the_foreground_is_locked_then_unlocked_after_the_delay() -> None:
    windows = FakeForeground()
    unlocked = threading.Event()
    original = windows.unlock

    def unlock() -> bool:
        result = original()
        unlocked.set()
        return result

    windows.unlock = unlock  # type: ignore[method-assign]
    assert hold_foreground(windows, seconds=0.01)
    assert unlocked.wait(5.0)
    assert windows.calls == ["lock", "unlock"]


def test_nothing_is_unlocked_when_the_lock_is_refused() -> None:
    windows = FakeForeground(lock_allowed=False)
    assert not hold_foreground(windows, seconds=0.01)
    assert windows.calls == ["lock"]
