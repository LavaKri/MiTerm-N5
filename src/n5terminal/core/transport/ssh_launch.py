"""The arguments and the environment of the ``ssh.exe`` that serves a connection.

See "How a connection is made" in ``specs/architecture/connection.md``. Nothing here starts a
process: ``SshLaunch`` says what to run, and ``ConPtyLaunch`` and ``SshTransport`` run it.

The target is validated first (``InvalidConnectionError``) and is given to ``ssh`` as an argument
of its own, after ``--``: ``ssh`` would take a target that starts with a dash for an option. The
environment holds the askpass program, the name of the pipe and the token: they are for ``ssh`` and
what it starts, not for the environment of MiTerm-N5, and they are never logged.
"""

import os
import secrets
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from n5terminal.askpass import CONNECTED_ARGUMENT, PIPE_VARIABLE, TOKEN_VARIABLE
from n5terminal.core.config.connections import is_valid_port, target_problem
from n5terminal.core.config.packaged import is_packaged
from n5terminal.core.errors import InvalidConnectionError

CONNECT_TIMEOUT = 15  # seconds before ``ssh`` gives up reaching the server
ALIVE_INTERVAL = 15  # seconds between two checks that the server answers
ALIVE_COUNT_MAX = 3  # checks that may fail: a cut is seen after 45 seconds at most


def system_ssh_path(environ: Mapping[str, str] | None = None) -> Path:
    """The ``ssh.exe`` of Windows, never the first one of the ``PATH`` (Git has its own)."""
    root = (os.environ if environ is None else environ).get("SystemRoot") or r"C:\Windows"
    return Path(root) / "System32" / "OpenSSH" / "ssh.exe"


def askpass_program_path() -> Path:
    """The program ``ssh`` runs to ask the user.

    ``MiTerm-N5-askpass.exe`` in the ``_internal`` folder once packaged; in development, the
    ``n5terminal-askpass.exe`` that ``pip install -e .`` puts next to ``python.exe`` (the
    application runs under ``pythonw.exe``).
    """
    if is_packaged():
        return Path(sys.executable).parent / "_internal" / "MiTerm-N5-askpass.exe"
    return Path(sys.executable).with_name("n5terminal-askpass.exe")


def new_pipe_name() -> str:
    """The name of a pipe for one connection: nobody can guess it."""
    return f"\\\\.\\pipe\\n5terminal-askpass-{secrets.token_hex(8)}"


def new_token() -> str:
    """A random value that only this connection and the program it runs share."""
    return secrets.token_hex(16)


@dataclass(slots=True, frozen=True)
class SshLaunch:
    """What to run for a connection: the target, the port, and how ``ssh`` reaches the app.

    ``ssh_program`` is ``None`` for the ``ssh.exe`` of Windows. ``known_hosts_file`` is set in the
    portable version, so that nothing is written outside its folder; ``None`` leaves the
    ``known_hosts`` of the system.
    """

    target: str
    askpass_program: Path
    pipe_name: str
    token: str
    port: int | None = None
    ssh_program: Path | None = None
    known_hosts_file: Path | None = None
    #: Arguments that come before the options: a script when ``ssh_program`` is an interpreter
    #: (the fake ``ssh`` of the tests). Empty for the real ``ssh.exe``.
    program_arguments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        problem = target_problem(self.target)
        if problem is not None:
            raise InvalidConnectionError("target", problem.value)
        if self.port is not None and not is_valid_port(self.port):
            raise InvalidConnectionError("port", str(self.port))

    @property
    def program(self) -> str:
        """The ``ssh`` to run."""
        return str(self.ssh_program or system_ssh_path())

    def arguments(self) -> tuple[str, ...]:
        """The program and its arguments, for ``ConPtyLaunch``: no remote command, so ``ssh``
        opens the shell of the server and asks for a terminal (its input is a pseudo console)."""
        options = [
            "PermitLocalCommand=yes",
            f'LocalCommand="{self.askpass_program}" {CONNECTED_ARGUMENT}',
            f"ConnectTimeout={CONNECT_TIMEOUT}",
            f"ServerAliveInterval={ALIVE_INTERVAL}",
            f"ServerAliveCountMax={ALIVE_COUNT_MAX}",
        ]
        if self.known_hosts_file is not None:
            # Forward slashes: a backslash is an escape in the options of ``ssh``.
            options.append(f'UserKnownHostsFile="{self.known_hosts_file.as_posix()}"')
        arguments = [self.program, *self.program_arguments]
        for option in options:
            arguments += ["-o", option]
        if self.port is not None:
            arguments += ["-p", str(self.port)]
        return (*arguments, "--", self.target)

    def environment(self, base: Mapping[str, str]) -> dict[str, str]:
        """``base`` with what makes ``ssh`` ask the user through the askpass program."""
        return {
            **base,
            "SSH_ASKPASS": str(self.askpass_program),
            "SSH_ASKPASS_REQUIRE": "force",
            PIPE_VARIABLE: self.pipe_name,
            TOKEN_VARIABLE: self.token,
        }
