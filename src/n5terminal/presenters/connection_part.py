"""The part of the session presenter that is about a connection to a server (a mixin).

Split from ``session_presenter.py`` (one subject per file, and that file was past its limit). A
connection is a run of the session like a program (see "What the session does" in
``specs/architecture/connection.md``); this holds what is its own: choosing it, opening it,
following its steps and its end. It uses the state of the presenter that inherits it: the
annotations below say which, and mypy checks them (``ConnectionChoice`` and ``connection_session``
hold the parts that need no state).
"""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from n5terminal.core.config.announcements import Announce
from n5terminal.core.config.connections import Connection
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import TransportError
from n5terminal.core.screen.line_analysis import LAUNCH_PREFIX
from n5terminal.core.session.launcher import Launcher
from n5terminal.core.session.session_state import Phase, SessionState
from n5terminal.core.transport.transport import TransportState
from n5terminal.i18n import _
from n5terminal.presenters.connection_interaction import ConnectionInteraction
from n5terminal.presenters.connection_session import (
    ConnectionChoice,
    connected_status,
    connection_end,
    start_failure,
)
from n5terminal.presenters.output_flow import OutputFlow
from n5terminal.presenters.profile_values import ProfileValues
from n5terminal.presenters.session_choices import SessionChoices
from n5terminal.presenters.session_info import (
    connection_dialog_title,
    connection_heading,
    connection_secret_title,
    connection_target_line,
    connection_where,
)
from n5terminal.presenters.session_run import (
    ConnectionRequest,
    LaunchRequest,
    Run,
    build_connection_run,
)
from n5terminal.presenters.session_view import SessionView


class ConnectionPart:
    """What a session presenter does for a connection."""

    # What the presenter gives it.
    _state: SessionState
    _run: Run | None
    _folder: Path
    _flow: OutputFlow
    _launcher: Launcher
    _settings: Settings
    _choices: SessionChoices
    _view: SessionView
    _clock: Callable[[], float]
    _last_end_text: str
    _connection: ConnectionChoice
    profile_values: ProfileValues
    post: Callable[[Callable[[], None]], None]

    if TYPE_CHECKING:

        def say(self, announce: Announce, **values: object) -> None: ...

        def _remember_command(self, run: Run, line: str) -> None: ...

        def _show_output(self) -> None: ...

        def _follow(self, run: Run, line: str) -> None: ...

        def _start(self, run: Run, request: LaunchRequest | None, echoed: int) -> None: ...

        def _launch_failed(self, announce: Announce, **values: object) -> None: ...

        def _write(self, run: Run, text: str) -> bool: ...

        def _refresh(self) -> None: ...

        def _set_state(self, state: SessionState) -> None: ...

    def _connect(self, text: str) -> None:
        """Open the connection that is chosen, as a run like any other.

        Its title and its target are written first, so that the output is not empty while the
        server says nothing; ``text`` is typed to the shell of the server once connected.
        """
        connection = self._connection.chosen
        if connection is None:
            return
        title = connection_dialog_title(connection.name, _)
        secret_title = connection_secret_title(connection.name, _)
        where = connection_where(connection.target, connection.port, _)
        interaction = ConnectionInteraction(self.post, self._view, title, secret_title, where)
        try:
            request = ConnectionRequest(
                connection,
                text,
                self._folder,
                self._choices.size.size,
                self._settings.ssh_path,
            )
            run = build_connection_run(self._launcher, self._flow.exchange, request, interaction)
        except TransportError as error:  # a target ssh would take for an option
            announce, values = start_failure(error)
            self._launch_failed(announce, **values)
            return
        run.status = _(Announce.CONNECTING.text)
        self._remember_command(run, text)
        target_line = connection_target_line(connection.target, connection.port, _)
        echoed = self._flow.echo(connection_heading(connection.name, _), LAUNCH_PREFIX, target_line)
        self._show_output()  # now, so that the first output cannot come before
        self._follow(run, text)
        self._start(run, None, echoed)

    @property
    def chosen_connection(self) -> Connection | None:
        """The connection the session goes through (``None``: Locale)."""
        return self._connection.chosen

    def select_connection(self, connection: Connection | None) -> bool:
        """Choose a connection, or ``None`` for Locale; only while nothing runs."""
        if not self._connection.choose(connection):
            return False
        self.profile_values.on_server = connection is not None
        return True

    @property
    def connection_target(self) -> str:
        """Where the chosen connection goes, as the output writes it (empty: Locale)."""
        connection = self._connection.chosen
        if connection is None:
            return ""
        port = connection.port
        return connection.target if port is None else f"{connection.target}:{port}"

    @property
    def connection_state(self) -> str:
        """The state of the chosen connection in words, as the status bar says it."""
        run = self._run
        if run is not None and run.connection is not None:
            return run.status
        return _("not connected")

    @property
    def connected_for(self) -> float | None:
        """For how many seconds the connection has been made (``None``: it is not)."""
        run = self._run
        if run is None or run.connected_at is None:
            return None
        return self._clock() - run.connected_at

    def refresh_connection(self, connection: Connection) -> None:
        """The chosen connection was edited: the session follows the new values."""
        self._connection.refresh(connection)

    def _handle_connection_state(self, run: Run, state: TransportState) -> None:
        """The steps of a connection: each is said once, and shown in the status bar."""
        connection = run.connection
        if connection is None:
            return
        if state is TransportState.CONNECTING:
            self._connection_step(run, Announce.CONNECTING, _(Announce.CONNECTING.text))
        elif state is TransportState.AUTHENTICATING:
            self._connection_step(run, Announce.AUTHENTICATING, _(Announce.AUTHENTICATING.text))
        elif state is TransportState.CONNECTED:
            run.connected, run.connected_at = True, self._clock()
            status = connected_status(connection.name, _)
            self._connection_step(run, Announce.CONNECTED, status, name=connection.name)
            if run.pending_line is not None:
                line, run.pending_line = run.pending_line, None
                self._write(run, line)
        elif state in (TransportState.CLOSED, TransportState.FAILED):
            self._connection_closed(run)

    def _connection_step(self, run: Run, announce: Announce, status: str, **values: object) -> None:
        run.status = status
        self.say(announce, **values)
        self._refresh()

    def _connection_closed(self, run: Run) -> None:
        """The connection is over: said, and written after the live part."""
        run.pump.finish()
        end = connection_end(run.transport, run.exit_code, _)
        self.say(end.announce, **end.values)
        self._flow.close_with(end.closing_line(_))
        self._last_end_text = end.status
        self._run = None
        self._set_state(replace(self._state, phase=Phase.IDLE, shell_at_prompt=False))
