"""The connection of a session: which one is chosen, and what is said of its start and its end.

Split from ``session_presenter.py`` (one subject per file). A connection is a run of the session
like a program (see "What the session does" in ``specs/architecture/connection.md``): this holds
what is its own. ``ConnectionChoice`` is the choice (Locale, or a connection), refused with its
reason while something runs; the functions say, without any state, how a start fails and how a
connection ends, as an announcement, a status text and the line of the closing part.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.config.connections import Connection
from n5terminal.core.errors import (
    AskpassNotFoundError,
    AuthenticationError,
    ConnectionFailedError,
    HostKeyError,
    ProgramNotFoundError,
    SshConnectionError,
    TransportError,
)
from n5terminal.core.session.session_state import CommandId, SessionState, refusal
from n5terminal.core.transport.transport import ConnectionReport
from n5terminal.i18n import N_

Translate = Callable[[str], str]
CONNECTED_STATUS = N_("Connected to {name}")
DISCONNECTED_STATUS = N_("Disconnected (code {code})")
CLOSED_STATUS = N_("Disconnected")
CANCELLED_STATUS = N_("Connection cancelled")
FAILED_STATUS = N_("Connection failed")


class ConnectionChoice:
    """The connection the session goes through (``None``: Locale). ``say`` announces a refusal."""

    def __init__(
        self,
        get_state: Callable[[], SessionState],
        set_state: Callable[[SessionState], None],
        say: Say,
    ) -> None:
        self._get_state = get_state
        self._set_state = set_state
        self._say = say
        self.chosen: Connection | None = None

    def choose(self, connection: Connection | None) -> bool:
        """Choose ``connection``, or ``None`` for Locale; only while nothing runs.

        Nothing is announced: the title of the window names the connection.
        """
        reason = refusal(CommandId.SET_CONNECTION, self._get_state())
        if reason is not None:
            self._say(reason)
            return False
        self.chosen = connection
        name = connection.name if connection is not None else None
        self._set_state(replace(self._get_state(), connection=name))
        return True

    def refresh(self, connection: Connection) -> None:
        """The chosen connection was edited (or renamed): the session follows the new one."""
        self.chosen = connection
        self._set_state(replace(self._get_state(), connection=connection.name))


@dataclass(slots=True, frozen=True)
class ConnectionEnd:
    """How a connection ended: what to announce, and what the status bar says from then on."""

    announce: Announce
    values: dict[str, object]
    status: str

    def closing_line(self, translate: Translate) -> str:
        """The line of the closing part: the announcement, written."""
        return translate(self.announce.text).format(**self.values)


def error_announcement(failure: SshConnectionError) -> tuple[Announce, dict[str, object]]:
    """The announcement of an error of the connection, with the line of ``ssh`` that explains it."""
    values: dict[str, object] = {"detail": failure.detail}
    if isinstance(failure, AuthenticationError):
        return Announce.AUTHENTICATION_FAILED, values
    if isinstance(failure, HostKeyError):
        return Announce.HOST_KEY_FAILED, values
    return Announce.CONNECTION_FAILED, values


def connection_end(transport: object, exit_code: int | None, translate: Translate) -> ConnectionEnd:
    """How the connection ended, from what its transport reports and the code of ``ssh``.

    An error is announced with its cause; a dialog the user cancelled is not an error; else the
    connection closed, with the code of ``ssh`` when it is known.
    """
    report = transport if isinstance(transport, ConnectionReport) else None
    failure = report.failure if report is not None else None
    if isinstance(failure, SshConnectionError):
        announce, values = error_announcement(failure)
        return ConnectionEnd(announce, values, translate(FAILED_STATUS))
    if report is not None and report.cancelled:
        return ConnectionEnd(Announce.CONNECTION_CANCELLED, {}, translate(CANCELLED_STATUS))
    if exit_code is None:
        return ConnectionEnd(Announce.CONNECTION_CLOSED, {}, translate(CLOSED_STATUS))
    return ConnectionEnd(
        announce=Announce.DISCONNECTED,  # (not said here: it is handed to ``say`` by the presenter)
        values={"code": exit_code},
        status=translate(DISCONNECTED_STATUS).format(code=exit_code),
    )


def start_failure(error: TransportError) -> tuple[Announce, dict[str, object]]:
    """What to say when the connection could not even be started.

    The program that asks the user and ``ssh.exe`` itself are told by their path; any other
    failure (the pipe, a target ``ssh`` would take for an option) is a plain failure to start.
    """
    if isinstance(error, AskpassNotFoundError):
        return Announce.ASKPASS_NOT_FOUND, {"program": error.program}
    if isinstance(error, ProgramNotFoundError):
        return Announce.SSH_NOT_FOUND, {"program": error.program}
    if isinstance(error, ConnectionFailedError):
        return Announce.CONNECTION_FAILED, {"detail": error.detail}
    return Announce.LAUNCH_FAILED, {"program": "SSH"}


def connected_status(name: str, translate: Translate) -> str:
    """The status bar once the connection is made."""
    return translate(CONNECTED_STATUS).format(name=name)
