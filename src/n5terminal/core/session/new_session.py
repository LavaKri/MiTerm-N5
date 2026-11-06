"""A new session is a new instance of the application.

See "Sessions" in ``specs/architecture/session.md``.

One window, one session, one process: a crash or a close never takes the other sessions down. The
new instance starts in the working folder of the current one.
"""

import subprocess
import sys
from pathlib import Path

from n5terminal.core.config.packaged import is_packaged
from n5terminal.core.errors import NewSessionError

DETACHED_PROCESS = 0x00000008


def new_session_command(
    folder: Path, data_folder: Path | None = None, develop: bool = False
) -> list[str]:
    """The command line that starts the application again, in ``folder``.

    The executable itself when packaged (``sys.frozen``), ``python -m n5terminal`` otherwise.
    ``data_folder`` is given on when this instance was started with ``--data-folder``, and
    ``--develop`` when it was started with it; the ``portable`` file beside the program needs no
    help, the new instance finds it.
    """
    if is_packaged():
        command = [sys.executable, "--folder", str(folder)]
    else:
        command = [sys.executable, "-m", "n5terminal", "--folder", str(folder)]
    if data_folder is not None:
        command += ["--data-folder", str(data_folder)]
    if develop:
        command.append("--develop")
    return command


def start_new_session(folder: Path, data_folder: Path | None = None, develop: bool = False) -> None:
    """Start another instance; it goes on if this one ends."""
    try:
        subprocess.Popen(
            new_session_command(folder, data_folder, develop),
            close_fds=True,
            creationflags=DETACHED_PROCESS,
        )
    except OSError as error:
        raise NewSessionError(str(error)) from error
