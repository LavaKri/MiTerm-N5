"""Signaling the activity of the output: the beep, or the line of an element.

``ActivityWatch`` keeps the flag; this decides, at each interval, what the user hears: nothing, a
beep, or the line of the caret said as the element it is. See "Activity detection" in
``specs/interface.md``.
"""

from n5terminal.core.config.announcements import (
    ACTIVITY,
    Announce,
    AnnouncementCenter,
    Destination,
    Say,
)
from n5terminal.core.config.settings import Settings
from n5terminal.core.screen.line_analysis import analyze_line
from n5terminal.core.session.session_state import Mode, Phase, SessionState
from n5terminal.presenters.activity_watch import ActivityWatch
from n5terminal.presenters.session_view import SessionView


class ActivitySignal:
    """The flag of the session and what is done with it."""

    def __init__(
        self, view: SessionView, settings: Settings, announcements: AnnouncementCenter, say: Say
    ) -> None:
        self._view = view
        self._settings = settings
        self._announcements = announcements
        self._say = say
        self._watch = ActivityWatch()

    def reset(self, now: float) -> None:
        """A program starts: forget the changes."""
        self._watch.reset(now)

    def sent(self, now: float) -> None:
        """The user sent something to the program: its echo is no activity."""
        self._watch.sent(now)

    def note(self, now: float) -> None:
        """The text of the output changed."""
        self._watch.note(now)

    def check(self, state: SessionState, now: float) -> None:
        """At each interval, signal the activity if the output changed: the element or a beep."""
        if state.phase is Phase.IDLE:
            self._watch.reset(now)
            return
        if not self._watch.check(now, self._settings.activity_interval):
            return
        destination = self._announcements.category_destination(ACTIVITY)
        if destination is Destination.NONE:
            return
        if self._settings.activity_only_in_output and not self._view.output_has_focus():
            return
        line, on_text = self._view.caret_line()
        element = analyze_line(
            line, selection_marks=state.mode is not Mode.PIPES, cursor_on_text=on_text
        )
        if element is not None:
            self._say(Announce.ACTIVITY, text=element.text)
        elif destination is Destination.ELEMENT_OR_BEEP:
            self._announcements.beep()
