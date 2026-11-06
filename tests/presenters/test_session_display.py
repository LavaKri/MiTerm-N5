from dataclasses import replace

import pytest

from fakes.fake_view import FakeView
from n5terminal.core.session.session_state import Interpreter, Phase, SessionState
from n5terminal.presenters.session_display import SessionDisplay
from n5terminal.presenters.session_view import InputMode

pytestmark = pytest.mark.unit


def display() -> tuple[SessionDisplay, FakeView]:
    view = FakeView()
    return SessionDisplay(view), view


def test_the_first_state_gives_the_window_everything() -> None:
    shown, view = display()
    shown.show(SessionState(), "Ready", "MiTerm-N5", "Command")
    assert len(view.shown_states) == 1
    assert len(view.enabled) == 1
    assert view.input_modes == [InputMode.COMMAND]
    assert view.input_labels == ["Command"]
    assert view.states == ["Ready"]
    assert view.titles == ["MiTerm-N5"]


def test_the_same_state_is_not_given_twice() -> None:
    shown, view = display()
    shown.show(SessionState(), "Ready", "MiTerm-N5", "Command")
    shown.show(SessionState(), "Ready", "MiTerm-N5", "Command")
    assert (len(view.shown_states), len(view.enabled), len(view.input_modes)) == (1, 1, 1)
    assert (len(view.states), len(view.titles)) == (1, 1)


def test_only_what_changed_is_given() -> None:
    shown, view = display()
    idle = SessionState()
    shown.show(idle, "Ready", "MiTerm-N5", "Command")
    shown.show(replace(idle, phase=Phase.RUNNING), "Running: ping", "MiTerm-N5", "Message")
    assert view.input_modes == [InputMode.COMMAND, InputMode.PROGRAM_INPUT]
    assert view.input_labels == ["Command", "Message"]
    assert view.states == ["Ready", "Running: ping"]
    assert len(view.enabled) == 2  # a running program changes the commands
    assert len(view.shown_states) == 1  # the choices of the menus did not change
    assert len(view.titles) == 1


def test_the_choices_of_the_menus_are_given_when_the_interpreter_changes() -> None:
    shown, view = display()
    shown.show(SessionState(), "Ready", "MiTerm-N5", "Command")
    shown.show(SessionState(interpreter=Interpreter.CMD), "Ready", "MiTerm-N5", "Command")
    assert len(view.shown_states) == 2
