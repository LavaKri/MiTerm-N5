"""The questions of a connection, from the thread of the transport to the window and back."""

import threading
from collections.abc import Callable

import pytest

from fakes.fake_view import FakeView
from n5terminal.presenters import connection_interaction
from n5terminal.presenters.connection_interaction import ConnectionInteraction

pytestmark = pytest.mark.unit


class UiThread:
    """The UI thread of the tests: what is posted waits here until the test runs it."""

    def __init__(self) -> None:
        self.posted: list[Callable[[], None]] = []
        self.arrived = threading.Event()

    def post(self, action: Callable[[], None]) -> None:
        self.posted.append(action)
        self.arrived.set()

    def run_next(self) -> None:
        assert self.arrived.wait(5)
        self.arrived.clear()
        self.posted.pop(0)()


def interaction(view: FakeView, ui: UiThread) -> ConnectionInteraction:
    return ConnectionInteraction(
        ui.post, view, "Connection to prod", "Connection prod: password", "admin@example.org"
    )


def ask_in_a_thread(call: Callable[[], object]) -> tuple[threading.Thread, list[object]]:
    answer: list[object] = []
    thread = threading.Thread(target=lambda: answer.append(call()), daemon=True)
    thread.start()
    return thread, answer


def test_the_host_key_question_is_asked_on_the_ui_thread_with_the_title_and_where() -> None:
    view, ui = FakeView(), UiThread()
    view.host_key_answers = [True]
    thread, answer = ask_in_a_thread(lambda: interaction(view, ui).confirm_host_key("Trust it?"))
    ui.run_next()
    thread.join(5)
    assert answer == [True]
    assert view.dialogs == [("host_key", "Connection to prod", "admin@example.org", "Trust it?")]


def test_the_secret_is_given_back_to_the_thread_that_asked() -> None:
    view, ui = FakeView(), UiThread()
    view.secret_answers = ["s3cr3t"]
    thread, answer = ask_in_a_thread(lambda: interaction(view, ui).ask_secret("password: "))
    ui.run_next()
    thread.join(5)
    assert answer == ["s3cr3t"]
    assert view.dialogs == [
        ("secret", "Connection prod: password", "admin@example.org", "password: ")
    ]


def test_a_cancelled_dialog_is_none_for_a_secret_and_no_for_a_host_key() -> None:
    view, ui = FakeView(), UiThread()
    first, secret = ask_in_a_thread(lambda: interaction(view, ui).ask_secret("password: "))
    ui.run_next()
    first.join(5)
    second, trusted = ask_in_a_thread(lambda: interaction(view, ui).confirm_host_key("Trust it?"))
    ui.run_next()
    second.join(5)
    assert (secret, trusted) == ([None], [False])


def test_the_thread_waits_for_the_answer_and_the_ui_thread_does_not_wait() -> None:
    view, ui = FakeView(), UiThread()
    view.secret_answers = ["x"]
    thread, answer = ask_in_a_thread(lambda: interaction(view, ui).ask_secret("password: "))
    assert ui.arrived.wait(5)
    assert thread.is_alive()  # nothing runs on the UI thread yet: the question waits there
    assert answer == []
    ui.run_next()
    thread.join(5)
    assert answer == ["x"]


def test_a_dialog_that_fails_does_not_leave_the_transport_waiting() -> None:
    ui = UiThread()

    class Broken(FakeView):
        def ask_secret(self, title: str, where: str, question: str) -> str | None:
            raise RuntimeError("the dialog could not open")

    thread, answer = ask_in_a_thread(lambda: interaction(Broken(), ui).ask_secret("password: "))
    with pytest.raises(RuntimeError):
        ui.run_next()
    thread.join(5)
    assert answer == [None]


def test_a_window_that_never_answers_is_a_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_interaction, "ANSWER_LIMIT", 0.05)
    assert interaction(FakeView(), UiThread()).ask_secret("password: ") is None
    assert interaction(FakeView(), UiThread()).confirm_host_key("Trust it?") is False


def test_withdrawing_closes_the_open_dialog_on_the_ui_thread() -> None:
    view, ui = FakeView(), UiThread()
    interaction(view, ui).withdraw()
    assert view.withdrawn_dialogs == 0  # posted, not done on the thread of the transport
    ui.run_next()
    assert view.withdrawn_dialogs == 1
