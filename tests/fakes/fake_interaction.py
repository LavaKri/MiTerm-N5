"""The user of a remote transport, driven by the test: answers given in advance, calls recorded.

A dialog can be held open (``hold``) to play the user taking his time; ``release`` lets it answer.
"""

import threading

WAIT = 10.0


class FakeInteraction:
    def __init__(
        self,
        host_keys: list[bool] | None = None,
        secrets: list[str | None] | None = None,
    ) -> None:
        self._host_keys = list(host_keys or [])
        self._secrets = list(secrets or [])
        self.host_key_texts: list[str] = []
        self.secret_questions: list[str] = []
        self.withdrawn = 0
        self.opened = threading.Event()  # a dialog is open
        self.hold = False  # the next dialog waits for ``release``
        self._release = threading.Event()

    def release(self) -> None:
        self._release.set()

    def confirm_host_key(self, text: str) -> bool:
        self.host_key_texts.append(text)
        if not self._wait():
            return False
        return self._host_keys.pop(0) if self._host_keys else False

    def ask_secret(self, question: str) -> str | None:
        self.secret_questions.append(question)
        if not self._wait():
            return None
        return self._secrets.pop(0) if self._secrets else None

    def withdraw(self) -> None:
        """Closing the dialog is a cancel, as the real one will be."""
        self.withdrawn += 1
        self._release.set()

    def _wait(self) -> bool:
        """Wait while the dialog is held; ``False`` if it was closed by ``withdraw``."""
        self.opened.set()
        if self.hold:
            before = self.withdrawn
            assert self._release.wait(WAIT), "the dialog was never released"
            return self.withdrawn == before
        return True
