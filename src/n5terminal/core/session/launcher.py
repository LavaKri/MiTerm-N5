"""Contract of what turns a command into a transport and the screen model that serves it.

The mode (CLI or TUI) is chosen by the user before the launch (menu Session > Mode); a shell that
stays open is always TUI. See "Choosing the mode" in ``specs/architecture.md``. The launcher only
builds; starting the transport, and the errors that come with it, belong to the caller.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from n5terminal.core.config.connections import Connection
from n5terminal.core.screen.screen_model import ScreenModel
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.session_state import LaunchMode, Mode
from n5terminal.core.transport.transport import Transport, TransportInteraction


@dataclass(slots=True, frozen=True)
class Launched:
    """A transport not started yet, how it is served, and the model that shows its output."""

    transport: Transport
    mode: Mode
    model: ScreenModel


@dataclass(slots=True, frozen=True)
class LaunchOptions:
    """What a launch can be asked besides the program: the standard error mark, the environment."""

    mark_stderr: bool = True
    environment: Mapping[str, str] | None = None  # replaces the environment (None: inherited)


class Launcher(Protocol):
    """Prepares the launch of one program."""

    def launch(
        self,
        arguments: tuple[str, ...],
        folder: Path,
        size: TerminalSize,
        *,
        launch_mode: LaunchMode,
        options: LaunchOptions | None = None,
    ) -> Launched:
        """Prepare ``arguments`` to run in ``folder``, served as ``launch_mode`` says.

        CLI gives pipes and a one-row screen model, which starts the lines of the standard error
        with a mark when ``options.mark_stderr``; TUI gives a pseudo console of ``size`` and a
        terminal screen model (one stream: nothing to mark). No ``options`` means the defaults.
        """
        ...

    def connect(
        self,
        connection: Connection,
        folder: Path,
        size: TerminalSize,
        interaction: TransportInteraction,
        *,
        ssh_path: str = "",
    ) -> Launched:
        """Prepare the connection to a server: always a terminal, whatever the launch mode.

        ``folder`` is where the local ``ssh`` runs (it means nothing on the server); ``interaction``
        asks the user what ``ssh`` asks; ``ssh_path`` is the ``ssh.exe`` to run (empty: the one of
        Windows). A refused target or port raises ``InvalidConnectionError``.
        """
        ...
