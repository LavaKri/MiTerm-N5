"""Announcements: what the application says about what it just did, and where it goes.

Every message is a member of ``Announce``. Most belong to a ``Category``: the user chooses a
``Destination`` per category (Preferences > Announcements), among the ones the category accepts,
not per message. The others are fixed: they are always said as a message. The code only calls
``AnnouncementCenter.notify``; how a message really reaches the user is the business of the sink
the center is connected to (see ``ui/message_sinks.py``).

The categories are a start: what is announced, and when, is still being settled with real use
(``specs/open-questions.md``).
"""

import enum
import string
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from n5terminal.core.errors import ScreenReaderOutputError
from n5terminal.i18n import N_, _


class Destination(enum.Enum):
    """What is done with the announcements of a category."""

    NONE = "none"
    MESSAGE = "message"  # the text of the announcement
    READ_LINE = "read_line"  # the text of the line concerned, given as ``line``
    DIALOG = "dialog"  # the text in a message box the user closes
    ELEMENT_OR_BEEP = "element_or_beep"  # the activity: the line of an element, else a beep
    ELEMENT = "element"  # the activity: only the line of an element

    @property
    def label(self) -> str:
        """Message id of the name shown in the Preferences (translate with ``_``)."""
        return _DESTINATION_LABELS[self]


_DESTINATION_LABELS = {
    Destination.NONE: N_("No announcement"),
    Destination.MESSAGE: N_("Message"),
    Destination.READ_LINE: N_("Read the line"),
    Destination.DIALOG: N_("Dialog box"),
    Destination.ELEMENT_OR_BEEP: N_("Messages or beep"),
    Destination.ELEMENT: N_("Messages"),
}


@dataclass(slots=True, frozen=True)
class Category:
    """A group of announcements that share one destination; ``label`` is a message id.

    ``choices`` are the destinations the user may pick (the first one is "nothing" by convention);
    ``default`` is one of them.
    """

    id: str
    label: str
    default: Destination
    choices: tuple[Destination, ...]

    def accepts(self, destination: Destination) -> bool:
        """Can the announcements of this category go to ``destination``?"""
        return destination in self.choices


_NONE_OR_MESSAGE = (Destination.NONE, Destination.MESSAGE)

#: A program starts, ends, is stopped, or leaves a process running.
PROGRAM = Category("program", N_("State of the program"), Destination.MESSAGE, _NONE_OR_MESSAGE)
#: A setting of the session changed: the working folder, the PowerShell.
FOLDER = Category("folder", N_("Session, settings"), Destination.MESSAGE, _NONE_OR_MESSAGE)
#: The session changed by itself: the terminal grew (automatic size), lines of the output were lost.
SESSION_CHANGE = Category(
    "session_change", N_("Session, change"), Destination.MESSAGE, _NONE_OR_MESSAGE
)
#: A jump to a title of the output (keys 1 to 6 and T) that arrived.
MOVEMENT = Category(
    "movement",
    N_("Output, movement and reading"),
    Destination.MESSAGE,
    (Destination.NONE, Destination.MESSAGE, Destination.READ_LINE),
)
#: A jump that reached nothing (no more title in that direction), or an identification that found
#: no element.
MOVEMENT_BLOCKED = Category(
    "movement_blocked",
    N_("Output, no more elements"),
    Destination.MESSAGE,
    _NONE_OR_MESSAGE,
)
#: The line of the caret read with its formatting (F4): the formatted text, or the line as it is.
LINE_READING = Category(
    "line_reading",
    N_("Output, read the line"),
    Destination.MESSAGE,
    (Destination.NONE, Destination.MESSAGE, Destination.READ_LINE),
)
#: A search that selected an occurrence.
SEARCH = Category("search", N_("Search reached"), Destination.MESSAGE, _NONE_OR_MESSAGE)
#: A search that found no more occurrence in the direction asked.
SEARCH_FAILED = Category(
    "search_failed",
    N_("Unsuccessful search"),
    Destination.MESSAGE,
    (Destination.NONE, Destination.MESSAGE, Destination.DIALOG),
)

#: A key was sent to the program (menu or shortcut).
KEY_SENT = Category("key_sent", N_("Output, keys sent"), Destination.MESSAGE, _NONE_OR_MESSAGE)

#: The output of a program changed (see "Activities" in ``specs/interface.md``). The line of the
#: caret is said when it is an element, else a beep (or nothing, with "Messages").
ACTIVITY = Category(
    "activity",
    N_("Terminal activity"),
    Destination.ELEMENT_OR_BEEP,
    (Destination.NONE, Destination.ELEMENT_OR_BEEP, Destination.ELEMENT),
)

#: The connection to a server changed state (connecting, authenticating, connected, closed,
#: cancelled).
#: The errors of a connection are in ``LAUNCH_FAILED``: an error is never switched off.
CONNECTION_STATE = Category(
    "connection_state", N_("Connection, state"), Destination.MESSAGE, _NONE_OR_MESSAGE
)

#: A command that cannot be done now, or that did nothing: the reason (this is also what a
#: shortcut of a greyed item says). A user who has a script of the screen reader may switch it off.
REFUSED = Category("refused", N_("Command not possible"), Destination.MESSAGE, _NONE_OR_MESSAGE)
#: A program, a PowerShell or a folder that could not be reached to start: never switched off.
LAUNCH_FAILED = Category(
    "launch_failed",
    N_("Launch failure"),
    Destination.MESSAGE,
    (Destination.MESSAGE, Destination.DIALOG),
)

#: Every category (the Announcements page of the Preferences sorts them by name).
CATEGORIES = (
    PROGRAM,
    FOLDER,
    SESSION_CHANGE,
    MOVEMENT,
    MOVEMENT_BLOCKED,
    LINE_READING,
    SEARCH,
    SEARCH_FAILED,
    KEY_SENT,
    ACTIVITY,
    CONNECTION_STATE,
    REFUSED,
    LAUNCH_FAILED,
)

# In the body of ``Announce`` a member hides the category of the same name: use these.
_KEY_SENT_CATEGORY = KEY_SENT
_ACTIVITY_CATEGORY = ACTIVITY
_LAUNCH_FAILED_CATEGORY = LAUNCH_FAILED
_CONNECTION_STATE_CATEGORY = CONNECTION_STATE


class Announce(enum.Enum):
    """All the messages of the application: a category (None: always said as a message) and
    ``text``, a message id (translate, then format)."""

    PROGRAM_STARTED = (PROGRAM, N_("Started: {program}."))
    PROGRAM_ENDED = (PROGRAM, N_("{program} ended with the code {code}."))
    PROGRAM_ENDED_UNKNOWN = (PROGRAM, N_("{program} ended."))
    PROGRAM_STOPPED = (PROGRAM, N_("Program stopped."))
    CHILD_ACTIVE = (PROGRAM, N_("A process started by the program is still running."))
    FOLDER_CHANGED = (FOLDER, N_("Working folder: {folder}."))
    SIZE_CHANGED = (SESSION_CHANGE, N_("Terminal size: {columns} columns, {rows} rows."))
    MOVED_TITLE = (MOVEMENT, N_("{title}, title {level}"))
    MOVED_TO_CURSOR = (MOVEMENT, N_("Terminal cursor: {line}"))
    MOVED_TO_EMULATOR_START = (MOVEMENT, N_("Start of the emulator: {line}"))
    MOVED_TO_EMULATOR_END = (MOVEMENT, N_("End of the emulator: {line}"))
    NO_NEXT_TITLE = (MOVEMENT_BLOCKED, N_("No next title."))
    NO_PREVIOUS_TITLE = (MOVEMENT_BLOCKED, N_("No previous title."))
    NO_NEXT_TITLE_OF_LEVEL = (MOVEMENT_BLOCKED, N_("No next title {level}."))
    NO_PREVIOUS_TITLE_OF_LEVEL = (MOVEMENT_BLOCKED, N_("No previous title {level}."))
    SEARCH_FOUND = (SEARCH, N_("{line}"))
    SEARCH_BAD_EXPRESSION = (SEARCH_FAILED, N_("The regular expression is not valid: {error}"))
    SEARCH_NO_NEXT = (SEARCH_FAILED, N_('No next occurrence of "{term}".'))
    SEARCH_NO_PREVIOUS = (SEARCH_FAILED, N_('No previous occurrence of "{term}".'))
    KEY_SENT = (_KEY_SENT_CATEGORY, N_("Sends {key}."))
    LINE_READ = (LINE_READING, N_("{text}"))
    COMFORT_LINE = (MOVEMENT, N_("{text}"))
    NO_PREVIOUS_LINE = (MOVEMENT_BLOCKED, N_("No previous line."))
    NO_NEXT_LINE = (MOVEMENT_BLOCKED, N_("No next line."))
    NO_ELEMENT_FOUND = (MOVEMENT_BLOCKED, N_("No element recognized."))
    HELP_NOT_FOUND = (REFUSED, N_("The help file {file} was not found."))
    HELP_NOT_OPENED = (REFUSED, N_("The help could not be opened in the browser."))
    ACTIVITY = (_ACTIVITY_CATEGORY, N_("{text}"))
    ACTIVITY_ON = (FOLDER, N_("Activity signaled."))
    # Not in ACTIVITY: switched off, that category would say nothing, not even this.
    ACTIVITY_OFF = (FOLDER, N_("Activity not signaled."))
    PROGRAM_NOT_FOUND = (_LAUNCH_FAILED_CATEGORY, N_("Program not found: {program}."))
    POWERSHELL_NOT_FOUND = (
        _LAUNCH_FAILED_CATEGORY,
        N_("Select a valid PowerShell. Not found: {path}."),
    )
    POWERSHELL_CHANGED = (FOLDER, N_("PowerShell: {powershell}."))
    SSH_CHANGED = (FOLDER, N_("OpenSSH client: {ssh}."))
    LAUNCH_FAILED = (_LAUNCH_FAILED_CATEGORY, N_("{program} could not be started."))
    INPUT_NOT_READ = (REFUSED, N_("Nothing sent: the program does not read its input."))
    FOLDER_NOT_FOUND = (_LAUNCH_FAILED_CATEGORY, N_("Folder not found: {folder}."))
    CONNECTING = (_CONNECTION_STATE_CATEGORY, N_("Connecting…"))
    AUTHENTICATING = (_CONNECTION_STATE_CATEGORY, N_("Authenticating…"))
    CONNECTED = (_CONNECTION_STATE_CATEGORY, N_("Connected to {name}."))
    DISCONNECTED = (_CONNECTION_STATE_CATEGORY, N_("Disconnected (code {code})."))
    CONNECTION_CLOSED = (_CONNECTION_STATE_CATEGORY, N_("Disconnected."))
    CONNECTION_CANCELLED = (_CONNECTION_STATE_CATEGORY, N_("Connection cancelled."))
    CONNECTION_FAILED = (_LAUNCH_FAILED_CATEGORY, N_("Connection failed: {detail}"))
    AUTHENTICATION_FAILED = (_LAUNCH_FAILED_CATEGORY, N_("Authentication refused: {detail}"))
    HOST_KEY_FAILED = (_LAUNCH_FAILED_CATEGORY, N_("Host key refused: {detail}"))
    SSH_NOT_FOUND = (_LAUNCH_FAILED_CATEGORY, N_("OpenSSH client not found: {program}."))
    ASKPASS_NOT_FOUND = (
        _LAUNCH_FAILED_CATEGORY,
        N_("The program that asks for passwords was not found: {program}."),
    )
    UNAVAILABLE_PROGRAM_RUNNING = (REFUSED, N_("Not available while a program is running."))
    UNAVAILABLE_CONNECTION_OPEN = (REFUSED, N_("Not available while a connection is open."))
    UNAVAILABLE_ON_CONNECTION = (REFUSED, N_("Not available with a connection."))
    UNAVAILABLE_NO_CONNECTION = (REFUSED, N_("No connection is chosen."))
    UNAVAILABLE_NO_CONNECTION_OPEN = (REFUSED, N_("No connection is open."))
    UNAVAILABLE_NO_PROGRAM = (REFUSED, N_("No program is running."))
    UNAVAILABLE_NO_OUTPUT = (REFUSED, N_("The output is empty."))
    UNAVAILABLE_NO_LAST_COMMAND = (REFUSED, N_("There is no command to resend."))
    HISTORY_EMPTY = (REFUSED, N_("No command typed yet."))
    UNAVAILABLE_NOT_TERMINAL = (REFUSED, N_("Only for programs that use a terminal."))
    UNAVAILABLE_SHELL_USES_TUI = (REFUSED, N_("A shell always uses the TUI mode."))
    UNAVAILABLE_PROFILE_CHOSEN = (REFUSED, N_("Not available while a profile is chosen."))
    UNAVAILABLE_NO_PROFILE = (REFUSED, N_("No profile is chosen."))
    UNAVAILABLE_NO_VARIABLES = (REFUSED, N_("The chosen profile uses no variable."))
    UNAVAILABLE_NO_PROFILE_PROGRAM = (REFUSED, N_("The chosen profile has no program."))
    SEND_REFUSED_CHILD_ACTIVE = (
        REFUSED,
        N_("Nothing sent: the program has ended and only a process it started is still running."),
    )
    COPIED = (SESSION_CHANGE, N_("Copied to the clipboard."))
    COPY_FAILED = (REFUSED, N_("Nothing copied: the clipboard is not available."))
    LINES_DROPPED = (
        SESSION_CHANGE,
        N_("The output keeps only the last {limit} lines: the oldest are dropped."),
    )
    LINES_LOST = (
        SESSION_CHANGE,
        N_("{count} lines of output were lost: they arrived faster than the window could show."),
    )

    def __init__(self, category: Category | None, text: str) -> None:
        self.category = category
        self.text = text

    @property
    def fields(self) -> frozenset[str]:
        """The names of the fields of the text: the values to give when the message is said."""
        parsed = string.Formatter().parse(self.text)
        return frozenset(name for _literal, name, _spec, _conversion in parsed if name is not None)


class Say(Protocol):
    """What a part of the application needs to announce something: ``SessionPresenter.say``."""

    def __call__(self, announce: Announce, **values: object) -> None: ...


class MessageSink(Protocol):
    """Receives the text to present to the user (through a screen reader, for instance)."""

    def show(self, text: str) -> None:
        """Present ``text``; raise ``ScreenReaderOutputError`` if it cannot be sent."""
        ...

    def close(self) -> None:
        """Release what the sink uses (when another sink replaces it)."""
        ...


class NullMessageSink:
    """The sink of the "no output" setting: the message goes nowhere."""

    def show(self, text: str) -> None:
        """Do nothing."""

    def close(self) -> None:
        """Nothing to release."""


class Beeper(Protocol):
    """Plays the short sound of the activity."""

    def beep(self) -> None:
        """Play the beep; it must not block the caller."""
        ...


class NullBeeper:
    """The beeper of tests and of a system with no sound: nothing is played."""

    def beep(self) -> None:
        """Do nothing."""


class AnnouncementCenter:
    """The single entry point for announcements.

    ``show_dialog`` shows a text in a message box (the ``DIALOG`` destination). If the sink fails,
    ``on_error`` is told (the user must know) and the center falls back to the null sink so that
    the failure is reported once rather than at every announcement.
    """

    def __init__(
        self,
        message_sink: MessageSink | None = None,
        destination_of: Callable[[Category], Destination] | None = None,
        on_error: Callable[[ScreenReaderOutputError], None] | None = None,
        show_dialog: Callable[[str], None] | None = None,
        beeper: Beeper | None = None,
    ) -> None:
        self.message_sink: MessageSink = message_sink or NullMessageSink()
        self.beeper: Beeper = beeper or NullBeeper()
        self._destination_of = destination_of or (lambda category: category.default)
        self._on_error = on_error
        self._show_dialog = show_dialog

    @staticmethod
    def text(announce: Announce, **values: object) -> str:
        """The text of ``announce`` filled with ``values``, without saying it."""
        return _(announce.text).format(**values)

    def destination(self, announce: Announce) -> Destination:
        """Where ``announce`` goes now (a fixed announcement is always a message)."""
        category = announce.category
        if category is None:
            return Destination.MESSAGE
        return self.category_destination(category)

    def category_destination(self, category: Category) -> Destination:
        """Where the announcements of ``category`` go now."""
        destination = self._destination_of(category)
        return destination if category.accepts(destination) else category.default

    def beep(self) -> None:
        """Play the beep of the activity."""
        self.beeper.beep()

    def notify(self, announce: Announce, **values: object) -> str | None:
        """Say ``announce`` (its text filled with ``values``) where its destination says.

        Returns the text that was sent to the sink, None if the announcement is a dialog or
        nothing.
        """
        destination = self.destination(announce)
        if destination is Destination.NONE:
            return None
        text = self.text(announce, **values)
        if destination is Destination.READ_LINE:
            text = str(values.get("line", text))
        if destination is Destination.DIALOG:
            if self._show_dialog is not None:
                self._show_dialog(text)
            return None
        self._show(text)
        return text

    def say_text(self, text: str) -> None:
        """Say ``text`` as a message, whatever the destinations chosen.

        For a text the user asks to hear (the result of a trial in a box): it is not one of the
        announcements of the application, which the user can route elsewhere or silence.
        """
        self._show(text)

    def _show(self, text: str) -> None:
        try:
            self.message_sink.show(text)
        except ScreenReaderOutputError as error:
            self.message_sink = NullMessageSink()
            if self._on_error is not None:
                self._on_error(error)
