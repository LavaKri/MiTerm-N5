"""A launcher that builds fake transports and real screen models, and remembers what was asked."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from fakes.fake_transport import FakeTransport
from n5terminal.core.config.connections import Connection
from n5terminal.core.screen.line_output_model import LineOutputModel
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.screen_model import ScreenModel
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.launcher import Launched, LaunchOptions
from n5terminal.core.session.session_state import LaunchMode, Mode
from n5terminal.core.transport.transport import TransportInteraction, TransportState


@dataclass(slots=True, frozen=True)
class ConnectCall:
    """A connection that was asked for: where, with which ``ssh``, and who answers its questions."""

    connection: Connection
    folder: Path
    size: TerminalSize
    interaction: TransportInteraction
    ssh_path: str


@dataclass(slots=True, frozen=True)
class LaunchCall:
    arguments: tuple[str, ...]
    folder: Path
    size: TerminalSize
    launch_mode: LaunchMode
    mark_stderr: bool = True
    environment: Mapping[str, str] | None = None


class FakeLauncher:
    """CLI gives pipes and TUI a terminal, unless ``mode`` forces one."""

    def __init__(self, mode: Mode | None = None) -> None:
        self.mode = mode
        self.calls: list[LaunchCall] = []
        self.transports: list[FakeTransport] = []
        self.start_error: Exception | None = None
        self.connections: list[ConnectCall] = []
        self.connect_error: Exception | None = None  # raised by ``connect``, as a bad target is
        # The states the transport of a connection goes through when it starts (None: the usual).
        self.start_states: tuple[TransportState, ...] | None = None

    @property
    def transport(self) -> FakeTransport:
        return self.transports[-1]

    def connect(
        self,
        connection: Connection,
        folder: Path,
        size: TerminalSize,
        interaction: TransportInteraction,
        *,
        ssh_path: str = "",
    ) -> Launched:
        if self.connect_error is not None:
            raise self.connect_error
        self.connections.append(ConnectCall(connection, folder, size, interaction, ssh_path))
        transport = FakeTransport()
        transport.start_error = self.start_error
        if self.start_states is not None:
            transport.start_states = self.start_states
        self.transports.append(transport)
        return Launched(transport, Mode.TERMINAL_LINE, PyteScreenModel(size.columns, size.rows))

    def launch(
        self,
        arguments: tuple[str, ...],
        folder: Path,
        size: TerminalSize,
        *,
        launch_mode: LaunchMode,
        options: LaunchOptions | None = None,
    ) -> Launched:
        options = options or LaunchOptions()
        mark_stderr = options.mark_stderr
        self.calls.append(
            LaunchCall(arguments, folder, size, launch_mode, mark_stderr, options.environment)
        )
        mode = self.mode or (Mode.TERMINAL_LINE if launch_mode is LaunchMode.TUI else Mode.PIPES)
        transport = FakeTransport()
        transport.start_error = self.start_error
        self.transports.append(transport)
        model: ScreenModel = (
            LineOutputModel(mark_stderr=mark_stderr)
            if mode is Mode.PIPES
            else PyteScreenModel(size.columns, size.rows)
        )
        return Launched(transport, mode, model)
