"""One launch of a program as the session presenter follows it, and what the presenter is given.

Split from ``session_presenter.py`` (one subject per file): this holds the data of a run, the
listener that hears its transport, and the services the presenter receives from outside.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from n5terminal.core.config.announcements import Announce, AnnouncementCenter
from n5terminal.core.config.connections import Connection
from n5terminal.core.config.settings import Settings
from n5terminal.core.errors import ProgramNotFoundError, TransportError, WorkingFolderError
from n5terminal.core.screen.display_exchange import DisplayExchange, ScreenPump
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.launcher import Launcher, LaunchOptions
from n5terminal.core.session.session_state import Interpreter, Mode, SessionState
from n5terminal.core.session.shell import shell_command, shell_environment
from n5terminal.core.transport.command_line import split_command_line
from n5terminal.core.transport.transport import (
    Stream,
    Transport,
    TransportInteraction,
    TransportState,
)

# After the end of a program, how long output may still come before it is said that a process it
# started goes on (a normal program is closed within a few milliseconds).
CHILD_GRACE = 1.0
LINE_END = {Mode.PIPES: b"\n", Mode.TERMINAL_LINE: b"\r", Mode.TERMINAL_SCREEN: b"\r"}


@dataclass(slots=True)
class Run:
    """One launch: its transport and what the presenter knows of it."""

    transport: Transport
    mode: Mode
    pump: ScreenPump
    program: str
    size: TerminalSize
    is_shell: bool
    pending_line: str | None  # typed before the shell was started, sent once it is connected
    prompt_prefix: str = ""  # what the shell was told to write before its prompt
    exit_code: int | None = None
    ended: bool = False
    child_since: float | None = None
    child_announced: bool = False
    connection: Connection | None = None  # set when the run is a connection to a server
    connected: bool = False  # the connection is made (its transport said so)
    connected_at: float | None = None  # the clock when it was made
    status: str = ""  # what the status bar says while the connection runs

    @property
    def types_lines(self) -> bool:
        """Is what is typed a line for a shell (kept as a command)? A shell, or a server's."""
        return self.is_shell or self.connection is not None

    @property
    def line_end(self) -> bytes:
        """A typed line ends with a line feed for pipes, a carriage return for a terminal."""
        return LINE_END[self.mode]


class RunEvents(Protocol):
    """What the listener of a run needs from the presenter."""

    post: Callable[[Callable[[], None]], None]

    def handle_state(self, run: Run, state: TransportState) -> None: ...

    def handle_exit(self, run: Run, exit_code: int | None) -> None: ...


class RunListener:
    """The ear of one transport: data on its thread, the other events on the UI thread."""

    def __init__(self, events: RunEvents, run: Run) -> None:
        self._events = events
        self._run = run

    def on_state_changed(self, state: TransportState) -> None:
        self._events.post(lambda: self._events.handle_state(self._run, state))

    def on_data(self, stream: Stream, data: bytes) -> None:
        self._run.pump.feed(data, stream)

    def on_exit(self, exit_code: int | None) -> None:
        self._events.post(lambda: self._events.handle_exit(self._run, exit_code))


@dataclass(slots=True, frozen=True)
class LaunchRequest:
    """What the user typed and the context it is launched in."""

    line: str
    state: SessionState
    folder: Path
    size: TerminalSize
    mark_stderr: bool = True
    prompt_prefix: str = ""  # for a shell that stays open: written before its prompt
    powershell_path: str = ""  # the PowerShell to start (empty: Windows PowerShell)


def build_run(launcher: Launcher, exchange: DisplayExchange, request: LaunchRequest) -> Run | None:
    """Prepare the launch of what the user typed; ``None`` for an empty line with no shell.

    Without a shell the line is split into the program and its arguments (the rules of Windows
    programs). With a shell the program is the shell, and the line is typed into it once it is
    connected (``pending_line``, ``None`` for an empty line).
    """
    line, state, size = request.line, request.state, request.size
    prefix = request.prompt_prefix
    shell = shell_command(state.interpreter, prefix, request.powershell_path)
    environment = None
    if shell is None:
        arguments = split_command_line(line)
        if not arguments:
            return None
        pending = None
    else:
        arguments, pending = shell, (line if line.strip() else None)
        environment = shell_environment(state.interpreter, prefix)
    launched = launcher.launch(
        arguments,
        request.folder,
        size,
        launch_mode=state.effective_launch_mode,
        options=LaunchOptions(request.mark_stderr, environment),
    )
    return Run(
        transport=launched.transport,
        mode=launched.mode,
        pump=ScreenPump(launched.model, exchange),
        program=Path(arguments[0]).name,
        size=size,
        is_shell=shell is not None,
        pending_line=pending,
        prompt_prefix=prefix if shell is not None else "",
    )


@dataclass(slots=True, frozen=True)
class ConnectionRequest:
    """What opens a connection: where, the text typed with it, and the context."""

    connection: Connection
    text: str  # typed to the shell of the server once connected
    folder: Path  # where the local ssh runs (it means nothing on the server)
    size: TerminalSize
    ssh_path: str = ""  # the ssh.exe to run (empty: the one of Windows)


def build_connection_run(
    launcher: Launcher,
    exchange: DisplayExchange,
    request: ConnectionRequest,
    interaction: TransportInteraction,
) -> Run:
    """Prepare the connection to a server.

    Raises ``InvalidConnectionError`` when ``ssh`` could not be given the target or the port.
    """
    connection, size = request.connection, request.size
    launched = launcher.connect(
        connection, request.folder, size, interaction, ssh_path=request.ssh_path
    )
    return Run(
        transport=launched.transport,
        mode=launched.mode,
        pump=ScreenPump(launched.model, exchange),
        program=f"SSH {connection.name}",
        size=size,
        is_shell=False,
        pending_line=request.text if request.text.strip() else None,
        connection=connection,
    )


def launch_failure(
    error: TransportError, request: LaunchRequest, program: str, is_shell: bool
) -> tuple[Announce, dict[str, object]]:
    """What to say when the transport could not start: the announcement and its values.

    A PowerShell the user chose that is not found is told by its path; a program, by its name.
    Any other failure of the start is a plain failure to launch.
    """
    if isinstance(error, ProgramNotFoundError):
        chosen = request.powershell_path
        if is_shell and request.state.interpreter is Interpreter.POWERSHELL and chosen:
            return Announce.POWERSHELL_NOT_FOUND, {"path": chosen}
        return Announce.PROGRAM_NOT_FOUND, {"program": program}
    if isinstance(error, WorkingFolderError):
        return Announce.FOLDER_NOT_FOUND, {"folder": request.folder}
    return Announce.LAUNCH_FAILED, {"program": program}


@dataclass(slots=True)
class SessionServices:
    """What the presenter needs from outside.

    ``post`` hands an action to the UI thread (``wx.CallAfter``); ``clock`` is replaced in tests.
    """

    launcher: Launcher
    settings: Settings
    announcements: AnnouncementCenter
    post: Callable[[Callable[[], None]], None]
    clock: Callable[[], float] = time.monotonic
