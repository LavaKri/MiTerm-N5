"""Fakes of what the announcement center talks to: a message sink and a beeper that record."""


class RecordingMessageSink:
    """Keeps the messages it receives."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def show(self, text: str) -> None:
        """Remember ``text``."""
        self.messages.append(text)

    def close(self) -> None:
        """Nothing to release."""


class RecordingBeeper:
    """Counts the beeps it is asked for."""

    def __init__(self) -> None:
        self.count = 0

    def beep(self) -> None:
        """Remember a beep."""
        self.count += 1
