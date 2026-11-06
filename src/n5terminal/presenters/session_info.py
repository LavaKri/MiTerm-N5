"""What the session tells about itself: the text of the information dialog, of the window title and
of the state in the status bar.

See "Session information" and "Status bar" in ``specs/interface.md``. Nothing here knows about
``wx``: the window gathers the values (``SessionInfo``) and shows the lines.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from n5terminal.core.session.session_state import Interpreter, Phase, SessionState
from n5terminal.core.transport.ssh_launch import system_ssh_path
from n5terminal.i18n import N_

Translate = Callable[[str], str]
LINE_FORMAT = N_("{name}: {value}")
FREE_PROFILE = N_("free profile")
TITLE_FORMAT = N_("MiTerm-N5: {profile} in {folder}")
CONNECTED_TITLE_FORMAT = N_("MiTerm-N5: {profile} on SSH {name}")
NOT_CONNECTED_TITLE_FORMAT = N_("MiTerm-N5: {profile} on SSH {name} (not connected)")
HEADING_FORMAT = N_("SSH {name}")
TARGET_FORMAT = N_("To {target}")
COMMAND_LABEL = N_("Command")
MESSAGE_LABEL = N_("Message")
DIALOG_TITLE_FORMAT = N_("Connection to {name}")
SECRET_TITLE_FORMAT = N_("Connection {name}: password")
WHERE_FORMAT = N_("{target}, port {port}")
FROM_FORMAT = N_("From {folder}")
READY = N_("Ready")
RUNNING_FORMAT = N_("Running: {program}")
CHILD_ACTIVE = N_("Child process active")
ENDED = N_("Ended")
ENDED_FORMAT = N_("Ended (code {code})")
INTERPRETER_NAMES = {
    Interpreter.NONE: N_("None"),
    Interpreter.CMD: "Cmd",
    Interpreter.POWERSHELL: "PowerShell",
}
NO_VALUE = N_("none")


def folder_text(folder: Path) -> str:
    """A folder as a path that ends with a separator (``C:\\test\\``)."""
    text = str(folder)
    return text if text.endswith(os.sep) else text + os.sep


def folder_name(folder: Path) -> str:
    """The last name of a folder (the whole path for a drive root)."""
    return folder.name or str(folder)


def window_title(profile: str | None, folder: Path, translate: Translate) -> str:
    """``MiTerm-N5: free profile in Dev``, or the name of the chosen profile."""
    return translate(TITLE_FORMAT).format(
        profile=profile if profile is not None else translate(FREE_PROFILE),
        folder=folder_name(folder),
    )


def connection_title(profile: str | None, name: str, connected: bool, translate: Translate) -> str:
    """``MiTerm-N5: free profile on SSH prod``, with ``(not connected)`` at the end until it is.

    That is the only state the title tells: the steps of the connection are in the status bar.
    """
    text = CONNECTED_TITLE_FORMAT if connected else NOT_CONNECTED_TITLE_FORMAT
    return translate(text).format(
        profile=profile if profile is not None else translate(FREE_PROFILE), name=name
    )


def connection_heading(name: str, translate: Translate) -> str:
    """The title written in the output when a connection opens: ``SSH prod`` (after ``# ``)."""
    return translate(HEADING_FORMAT).format(name=name)


def connection_target_line(target: str, port: int | None, translate: Translate) -> str:
    """The line under it: ``To admin@example.org:2222``."""
    place = target if port is None else f"{target}:{port}"
    return translate(TARGET_FORMAT).format(target=place)


def connection_dialog_title(name: str, translate: Translate) -> str:
    """The title of the dialogs of a connection: ``Connection to prod``."""
    return translate(DIALOG_TITLE_FORMAT).format(name=name)


def input_label(state: SessionState, profile: str, translate: Translate) -> str:
    """The name of the command field: ``Command``, the profile whose program it takes the
    arguments of, or ``Message`` for a program that runs.

    ``profile`` is the name of the chosen profile, as the user wrote it, when it has a program
    that takes arguments (empty: none). A shell that runs, and a connection, take commands; a
    server is not given the program of a profile.
    """
    if state.phase is Phase.IDLE:
        return profile if profile and not state.on_server else translate(COMMAND_LABEL)
    if state.on_server or state.shell_ready:
        return translate(COMMAND_LABEL)
    return translate(MESSAGE_LABEL)


def connection_secret_title(name: str, translate: Translate) -> str:
    """The title of the dialog that asks for a secret: ``Connection prod: password``.

    The screen reader reads the title when the dialog opens, so it says what is asked for.
    """
    return translate(SECRET_TITLE_FORMAT).format(name=name)


def connection_where(target: str, port: int | None, translate: Translate) -> str:
    """Where a connection goes, for its dialogs: ``admin@example.org, port 2222``."""
    if port is None:
        return target
    return translate(WHERE_FORMAT).format(target=target, port=port)


def launch_folder_line(folder: Path, translate: Translate) -> str:
    """The line under the title of a launched command: ``From C:\\test\\``."""
    return translate(FROM_FORMAT).format(folder=folder_text(folder))


def end_text(exit_code: int | None, translate: Translate) -> str:
    """How a program ended, as the status bar says it: with its code when it is known."""
    if exit_code is None:
        return translate(ENDED)
    return translate(ENDED_FORMAT).format(code=exit_code)


def run_text(
    program: str | None, child_announced: bool, last_end: str, translate: Translate
) -> str:
    """The state in the status bar.

    ``program`` is the one that runs (``None``: none); ``child_announced``, whether it is said that
    a process it started goes on after its end; ``last_end``, how the last program ended (empty:
    none ended yet).
    """
    if program is None:
        return last_end or translate(READY)
    if child_announced:
        return translate(CHILD_ACTIVE)
    return translate(RUNNING_FORMAT).format(program=program)


@dataclass(slots=True, frozen=True)
class SessionInfo:
    """The values the information dialog shows."""

    folder: Path
    profile: str | None
    program: str | None
    last_end: str
    launch_mode: str  # "CLI" or "TUI"
    interpreter: Interpreter
    terminal_size: str  # "80 x 24"
    terminal_view_only: bool
    output_lines: int
    output_limit: int
    data_mode: str  # "normal", "portable" or "develop" (message ids)
    settings_file: Path | None
    profiles_folder: Path | None
    log_file: Path | None
    version: str
    # The connection chosen (None: Locale), its target, its state, and for how long it is open.
    connection: str | None = None
    connection_target: str = ""
    connection_state: str = ""
    connected_for: float | None = None  # seconds
    ssh_path: str = ""  # the ssh.exe set (empty: the one of Windows)
    connections_folder: Path | None = None


def duration_text(seconds: float, translate: Translate) -> str:
    """How long, in words: ``45 s``, ``12 min``, ``2 h 5 min``."""
    whole = int(seconds)
    if whole < 60:
        return translate(N_("{seconds} s")).format(seconds=whole)
    minutes = whole // 60
    if minutes < 60:
        return translate(N_("{minutes} min")).format(minutes=minutes)
    return translate(N_("{hours} h {minutes} min")).format(
        hours=minutes // 60, minutes=minutes % 60
    )


def _connection_lines(
    info: SessionInfo, line: Callable[[str, object], str], translate: Translate
) -> list[str]:
    """The lines of the connection chosen: none for Locale."""
    if info.connection is None:
        return []
    state = info.connection_state
    if info.connected_for is not None:
        since = translate(N_("since {duration}")).format(
            duration=duration_text(info.connected_for, translate)
        )
        state = f"{state}, {since}"
    return [
        line(N_("Connection"), info.connection),
        line(N_("Target"), info.connection_target),
        line(N_("Connection state"), state),
    ]


def session_info_lines(info: SessionInfo, translate: Translate) -> list[str]:
    """One line per information, ``Name: value``."""

    def line(name: str, value: object) -> str:
        return translate(LINE_FORMAT).format(name=translate(name), value=value)

    def path(value: Path | None) -> str:
        return str(value) if value is not None else translate(NO_VALUE)

    return [
        line(N_("Working folder"), info.folder),
        *_connection_lines(info, line, translate),
        line(N_("Session type"), translate(info.data_mode)),
        line(N_("Profile"), info.profile if info.profile is not None else translate(FREE_PROFILE)),
        line(N_("Running program"), info.program or translate(NO_VALUE)),
        line(N_("Last end"), info.last_end or translate(NO_VALUE)),
        line(N_("Launch mode"), info.launch_mode),
        line(N_("Interpreter"), translate(INTERPRETER_NAMES[info.interpreter])),
        line(N_("Terminal size"), info.terminal_size),
        line(
            N_("Terminal view only"),
            translate(N_("Yes") if info.terminal_view_only else N_("No")),
        ),
        line(
            N_("Output lines"),
            translate(N_("{lines} of {limit}")).format(
                lines=info.output_lines, limit=info.output_limit
            ),
        ),
        line(N_("Settings file"), path(info.settings_file)),
        line(N_("Profiles folder"), path(info.profiles_folder)),
        line(N_("Connections folder"), path(info.connections_folder)),
        line(N_("OpenSSH client"), info.ssh_path or str(system_ssh_path())),
        line(N_("Log file"), path(info.log_file)),
        line(N_("Version"), info.version),
    ]
