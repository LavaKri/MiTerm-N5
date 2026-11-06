import ctypes
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

import pytest

from n5terminal.askpass import PIPE_VARIABLE, TOKEN_VARIABLE
from n5terminal.core.errors import InvalidConnectionError
from n5terminal.core.transport.ssh_launch import SshLaunch, askpass_program_path, system_ssh_path

pytestmark = pytest.mark.unit

ASKPASS = Path(r"C:\Program Files\MiTerm-N5\MiTerm-N5-askpass.exe")
PIPE = r"\\.\pipe\n5terminal-askpass-0123"
SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"


def test_the_packaged_askpass_program_is_in_the_internal_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\MiTerm-N5\MiTerm-N5.exe")
    assert askpass_program_path() == Path(r"C:\Apps\MiTerm-N5\_internal\MiTerm-N5-askpass.exe")


def test_the_askpass_program_of_a_source_run_is_the_one_pip_installs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "executable", r"C:\Dev\.venv\Scripts\pythonw.exe")
    assert askpass_program_path() == Path(r"C:\Dev\.venv\Scripts\n5terminal-askpass.exe")


def launch(**changes: object) -> SshLaunch:
    values: dict[str, object] = {
        "target": "admin@example.org",
        "askpass_program": ASKPASS,
        "pipe_name": PIPE,
        "token": "t0k3n",
        "ssh_program": Path(SSH),
    }
    return SshLaunch(**{**values, **changes})  # type: ignore[arg-type]


def argv(command_line: str) -> list[str]:
    """What a program started with ``command_line`` sees as its arguments (the C runtime rules)."""
    shell32 = ctypes.windll.shell32
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    count = ctypes.c_int()
    pointer = shell32.CommandLineToArgvW(command_line, ctypes.byref(count))
    return [pointer[index] for index in range(count.value)]


# The arguments ---------------------------------------------------------------------------------


def test_the_arguments_of_a_connection() -> None:
    assert launch().arguments() == (
        SSH,
        "-o",
        "PermitLocalCommand=yes",
        "-o",
        f'LocalCommand="{ASKPASS}" --connected',
        "-o",
        "ConnectTimeout=15",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=3",
        "--",
        "admin@example.org",
    )


def test_the_target_comes_last_after_the_options_and_after_the_double_dash() -> None:
    arguments = launch(port=2222).arguments()
    assert arguments[-3:] == ("2222", "--", "admin@example.org")
    assert arguments[-4] == "-p"


def test_no_port_means_no_option_for_it() -> None:
    assert "-p" not in launch().arguments()


def test_the_known_hosts_file_of_the_portable_version_is_given_with_forward_slashes() -> None:
    folder = Path(r"E:\Mes clés\data")
    arguments = launch(known_hosts_file=folder / "known_hosts").arguments()
    assert 'UserKnownHostsFile="E:/Mes clés/data/known_hosts"' in arguments


def test_without_a_known_hosts_file_the_one_of_the_system_is_left_alone() -> None:
    assert not any("UserKnownHostsFile" in argument for argument in launch().arguments())


def test_there_is_no_remote_command_and_no_option_that_forces_a_terminal() -> None:
    """ssh opens the shell of the server and asks for a terminal because its input is a console."""
    arguments = launch().arguments()
    assert arguments[-1] == "admin@example.org"
    assert "-t" not in arguments
    assert "-tt" not in arguments


@pytest.mark.skipif(sys.platform != "win32", reason="the command line of Windows")
def test_ssh_gets_every_argument_back_as_it_was_given() -> None:
    """The quotes of LocalCommand, the spaces of the paths: through the command line of Windows."""
    folder = Path(r"C:\Dossier avec espace")
    arguments = launch(
        port=22, known_hosts_file=folder / "known_hosts", askpass_program=folder / "askpass.exe"
    ).arguments()
    seen = argv(subprocess.list2cmdline(arguments))
    assert seen == list(arguments)
    assert f'LocalCommand="{folder / "askpass.exe"}" --connected' in seen


def test_a_program_of_choice_is_used() -> None:
    assert launch(ssh_program=Path(r"D:\tools\ssh.exe")).arguments()[0] == r"D:\tools\ssh.exe"


def test_the_ssh_of_windows_is_in_the_folder_of_the_system_not_in_the_path() -> None:
    assert system_ssh_path({"SystemRoot": r"D:\Win"}) == Path(r"D:\Win\System32\OpenSSH\ssh.exe")
    assert system_ssh_path({}) == Path(r"C:\Windows\System32\OpenSSH\ssh.exe")
    assert launch(ssh_program=None).program == str(system_ssh_path())


# The environment -------------------------------------------------------------------------------


def test_the_environment_makes_ssh_ask_through_the_askpass_program() -> None:
    environment = launch().environment({"PATH": "C:\\bin", "SSH_ASKPASS": "other"})
    assert environment == {
        "PATH": "C:\\bin",
        "SSH_ASKPASS": str(ASKPASS),
        "SSH_ASKPASS_REQUIRE": "force",
        PIPE_VARIABLE: PIPE,
        TOKEN_VARIABLE: "t0k3n",
    }


def test_the_environment_given_is_not_changed() -> None:
    base = {"PATH": "x"}
    launch().environment(base)
    assert base == {"PATH": "x"}


# The target is checked before anything is run --------------------------------------------------


@pytest.mark.parametrize(
    ("target", "problem"),
    [
        ("-oProxyCommand=calc", "option_like"),
        ("admin@-oProxyCommand=calc", "option_like"),
        ("a b", "forbidden_character"),
        ("", "empty"),
        ("admin@", "empty"),
    ],
)
def test_a_target_ssh_could_take_for_something_else_is_refused(target: str, problem: str) -> None:
    with pytest.raises(InvalidConnectionError) as refused:
        launch(target=target)
    assert (refused.value.field, refused.value.problem) == ("target", problem)


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_a_port_out_of_range_is_refused(port: int) -> None:
    with pytest.raises(InvalidConnectionError) as refused:
        launch(port=port)
    assert refused.value.field == "port"
