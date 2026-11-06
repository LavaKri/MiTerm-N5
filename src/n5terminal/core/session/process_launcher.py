"""The launcher of the application: CLI gives pipes, TUI gives a pseudo console.

See "Choosing the mode" in ``specs/architecture.md``. It only builds: the transport is not started
here, so the errors of the start (program not found, folder missing) reach the caller.
"""

from pathlib import Path

from n5terminal.core.config.connections import Connection
from n5terminal.core.screen.line_output_model import LineOutputModel
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.launcher import Launched, LaunchOptions
from n5terminal.core.session.session_state import LaunchMode, Mode
from n5terminal.core.transport.conpty_transport import ConPtyLaunch, ConPtyTransport
from n5terminal.core.transport.pipe_transport import PipeLaunch, PipeTransport
from n5terminal.core.transport.ssh_launch import (
    SshLaunch,
    askpass_program_path,
    new_pipe_name,
    new_token,
)
from n5terminal.core.transport.ssh_transport import SshTransport
from n5terminal.core.transport.transport import TransportInteraction


class ProcessLauncher:
    """:class:`~n5terminal.core.session.launcher.Launcher` for the programs of this computer, and
    for the connections to servers (through the ``ssh.exe`` of this computer).

    ``known_hosts_file`` is set in the portable version, so that ``ssh`` writes the host keys in
    the folder of the application and not in the profile of the Windows user.
    """

    def __init__(self, known_hosts_file: Path | None = None) -> None:
        self._known_hosts_file = known_hosts_file

    def connect(
        self,
        connection: Connection,
        folder: Path,
        size: TerminalSize,
        interaction: TransportInteraction,
        *,
        ssh_path: str = "",
    ) -> Launched:
        launch = SshLaunch(
            target=connection.target,
            askpass_program=askpass_program_path(),
            pipe_name=new_pipe_name(),
            token=new_token(),
            port=connection.port,
            ssh_program=Path(ssh_path) if ssh_path else None,
            known_hosts_file=self._known_hosts_file,
        )
        transport = SshTransport(launch, interaction, folder, size=(size.columns, size.rows))
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
        if launch_mode is LaunchMode.CLI:
            return Launched(
                PipeTransport(PipeLaunch(arguments, folder, options.environment)),
                Mode.PIPES,
                LineOutputModel(mark_stderr=options.mark_stderr),
            )
        transport = ConPtyTransport(
            ConPtyLaunch(arguments, folder, options.environment, size.columns, size.rows)
        )
        return Launched(transport, Mode.TERMINAL_LINE, PyteScreenModel(size.columns, size.rows))
