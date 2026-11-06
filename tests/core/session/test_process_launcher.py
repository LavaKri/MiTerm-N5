from pathlib import Path

import pytest

from n5terminal.core.config.connections import Connection
from n5terminal.core.errors import InvalidConnectionError
from n5terminal.core.screen.line_output_model import LineOutputModel
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.terminal_size import TerminalSize
from n5terminal.core.session.process_launcher import ProcessLauncher
from n5terminal.core.session.session_state import LaunchMode, Mode
from n5terminal.core.transport.conpty_transport import ConPtyTransport
from n5terminal.core.transport.pipe_transport import PipeTransport
from n5terminal.core.transport.ssh_launch import SshLaunch, system_ssh_path
from n5terminal.core.transport.ssh_transport import SshTransport

pytestmark = pytest.mark.unit

SIZE = TerminalSize(100, 30)


def test_cli_gives_pipes_and_a_one_row_model() -> None:
    launched = ProcessLauncher().launch(("prog",), Path.cwd(), SIZE, launch_mode=LaunchMode.CLI)
    assert isinstance(launched.transport, PipeTransport)
    assert launched.mode is Mode.PIPES
    assert isinstance(launched.model, LineOutputModel)


def test_tui_gives_a_pseudo_console_and_a_screen_of_the_size_asked() -> None:
    launched = ProcessLauncher().launch(("prog",), Path.cwd(), SIZE, launch_mode=LaunchMode.TUI)
    assert isinstance(launched.transport, ConPtyTransport)
    assert launched.mode is Mode.TERMINAL_LINE
    assert isinstance(launched.model, PyteScreenModel)
    assert (launched.model.columns, launched.model.row_count) == (100, 30)


def test_nothing_is_started_by_the_launcher() -> None:
    launched = ProcessLauncher().launch(
        ("no-such-program",), Path.cwd(), SIZE, launch_mode=LaunchMode.CLI
    )
    assert launched.transport.state.value == "closed"


# A connection ----------------------------------------------------------------------------------


class Nobody:
    """The user, for a transport that is built and never started."""

    def confirm_host_key(self, text: str) -> bool:
        return False

    def ask_secret(self, question: str) -> str | None:
        return None

    def withdraw(self) -> None:
        pass


PROD = Connection("prod", target="admin@example.org", port=2222)


def test_a_connection_gives_an_ssh_transport_and_a_terminal_of_the_size_asked() -> None:
    launched = ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody())
    assert isinstance(launched.transport, SshTransport)
    assert launched.mode is Mode.TERMINAL_LINE
    assert isinstance(launched.model, PyteScreenModel)
    assert (launched.model.columns, launched.model.row_count) == (100, 30)


def test_a_connection_is_always_a_terminal_whatever_the_launch_mode_of_the_session() -> None:
    """There is no ``launch_mode`` to give: ssh needs a console to ask for a terminal."""
    launched = ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody())
    assert launched.transport.state.value == "closed"  # built, not started


def test_the_ssh_chosen_is_the_one_that_will_run(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[SshLaunch] = []
    real = SshTransport

    def spy(launch: SshLaunch, *rest: object, **keywords: object) -> SshTransport:
        seen.append(launch)
        return real(launch, *rest, **keywords)  # type: ignore[arg-type]

    monkeypatch.setattr("n5terminal.core.session.process_launcher.SshTransport", spy)
    ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody(), ssh_path=r"C:\Git\usr\bin\ssh.exe")
    ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody())
    assert seen[0].program == r"C:\Git\usr\bin\ssh.exe"
    assert seen[1].program == str(system_ssh_path())


def test_a_known_hosts_file_is_given_to_ssh_in_the_portable_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[SshLaunch] = []
    real = SshTransport

    def spy(launch: SshLaunch, *rest: object, **keywords: object) -> SshTransport:
        seen.append(launch)
        return real(launch, *rest, **keywords)  # type: ignore[arg-type]

    monkeypatch.setattr("n5terminal.core.session.process_launcher.SshTransport", spy)
    ProcessLauncher(tmp_path / "known_hosts").connect(PROD, Path.cwd(), SIZE, Nobody())
    ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody())
    assert seen[0].known_hosts_file == tmp_path / "known_hosts"
    assert seen[1].known_hosts_file is None  # the known_hosts of the system is left alone


def test_a_target_ssh_would_take_for_an_option_is_refused_before_anything_is_built() -> None:
    with pytest.raises(InvalidConnectionError):
        ProcessLauncher().connect(
            Connection("x", target="-oProxyCommand=calc"), Path.cwd(), SIZE, Nobody()
        )


def test_each_connection_gets_its_own_pipe_and_token(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[SshLaunch] = []
    real = SshTransport

    def spy(launch: SshLaunch, *rest: object, **keywords: object) -> SshTransport:
        seen.append(launch)
        return real(launch, *rest, **keywords)  # type: ignore[arg-type]

    monkeypatch.setattr("n5terminal.core.session.process_launcher.SshTransport", spy)
    for _ in range(2):
        ProcessLauncher().connect(PROD, Path.cwd(), SIZE, Nobody())
    assert seen[0].pipe_name != seen[1].pipe_name
    assert seen[0].token != seen[1].token
    assert seen[0].pipe_name.startswith(r"\\.\pipe\n5terminal-askpass-")
