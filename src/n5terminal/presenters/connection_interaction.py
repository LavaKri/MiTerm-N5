"""What a connection asks the user, from the thread of the transport to the window.

The transport (``SshTransport``) asks from its own thread and waits for the answer (the contract
``TransportInteraction`` of ``core/transport/transport.py``). The window is the UI thread's: each
question is posted there, the dialog opens, and the answer comes back through an event. The UI
thread is never blocked, and the transport thread waits no longer than the program that asked on
behalf of ``ssh`` does (it gives up after ``askpass.ASK_LIMIT`` seconds).
"""

import threading
from collections.abc import Callable

from n5terminal.askpass import ASK_LIMIT
from n5terminal.presenters.session_view import DialogView

#: A little more than the program waits: if the window never answers, the question is cancelled.
ANSWER_LIMIT = ASK_LIMIT + 30.0


class ConnectionInteraction:
    """Implements ``TransportInteraction`` for one connection.

    ``title`` and ``where`` are given to the dialogs, so that they say which connection asks and
    where it goes; the question for a secret has its own title, ``secret_title``, which also says
    what is asked for.
    """

    def __init__(
        self,
        post: Callable[[Callable[[], None]], None],
        view: DialogView,
        title: str,
        secret_title: str,
        where: str,
    ) -> None:
        self._post = post
        self._view = view
        self._title = title
        self._secret_title = secret_title
        self._where = where

    def confirm_host_key(self, text: str) -> bool:
        """Ask whether to trust the server; a window that does not answer is a no."""
        return self._ask(lambda: self._view.confirm_host_key(self._title, self._where, text), False)

    def ask_secret(self, question: str) -> str | None:
        """Ask for a secret; ``None`` when cancelled, or when the window does not answer."""
        return self._ask(
            lambda: self._view.ask_secret(self._secret_title, self._where, question), None
        )

    def withdraw(self) -> None:
        """Close the dialog still open (its question is not waiting for an answer any more)."""
        self._post(self._view.withdraw_dialog)

    def _ask[T](self, ask: Callable[[], T], unanswered: T) -> T:
        done = threading.Event()
        answer: list[T] = [unanswered]

        def run() -> None:
            try:
                answer[0] = ask()
            finally:
                done.set()  # whatever happens in the dialog, the transport must not wait for ever

        self._post(run)
        done.wait(ANSWER_LIMIT)
        return answer[0]
