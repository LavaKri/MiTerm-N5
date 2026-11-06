"""The activity flag: did the output change since the last check, one check per interval?

A change of the text of the output raises the flag (``note``); every ``interval`` seconds the
session asks ``check``, which lowers the flag and says whether it was up. There is no memory of what
was said: a bar that stands still is said again with the same value as long as the output changes
elsewhere, and nothing is said when the output no longer changes. What an activity is said as is
the business of the session (``specs/interface.md``, "Activity detection"). The clock is given, so
that this is tested without waiting.
"""

ECHO_GRACE = 0.3  # seconds after something was sent in which a change is the echo of it


class ActivityWatch:
    """The flag and the time of the last check."""

    def __init__(self) -> None:
        self._flag = False
        self._last_check = 0.0
        self._echo_until = 0.0

    def reset(self, now: float) -> None:
        """A program starts or ends: forget the changes, and count the interval from ``now``."""
        self._flag = False
        self._last_check = now
        self._echo_until = 0.0

    def sent(self, now: float) -> None:
        """The user sent something to the program: what it echoes within a moment is no activity."""
        self._echo_until = now + ECHO_GRACE

    def note(self, now: float) -> None:
        """The text of the output changed."""
        if now >= self._echo_until:
            self._flag = True

    def check(self, now: float, interval: float) -> bool:
        """Is it time to look at the flag, and was it up? Lowers it when it is time."""
        if now - self._last_check < interval:
            return False
        self._last_check = now
        raised, self._flag = self._flag, False
        return raised
