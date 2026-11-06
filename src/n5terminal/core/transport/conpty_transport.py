"""Local transport through a Windows pseudo console (ConPTY): the TUI modes 4 and 5.

One thread, the pump, owns the pseudo console: it applies a pending resize, writes the queued
input, reads the output and watches the end of the program. pywinpty returns decoded text; it is
encoded back to UTF-8 to keep the bytes contract of ``Transport`` (see the ConPTY experiment in
``specs/architecture/stack.md``).
"""

import codecs
import logging
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import winpty

from n5terminal.core.errors import (
    InputQueueFullError,
    LaunchError,
    ProcessTreeError,
    ProgramNotFoundError,
    TransportClosedError,
    TransportError,
    WorkingFolderError,
)
from n5terminal.core.transport.foreground import Win32Foreground, hold_foreground
from n5terminal.core.transport.process_tree import (
    ProcessTree,
    hold_process_tree,
    keep_children,
    terminate_tree,
)
from n5terminal.core.transport.transport import Stream, TransportListener, TransportState

logger = logging.getLogger(__name__)

DEFAULT_COLUMNS = 80
DEFAULT_ROWS = 24
POLL = 0.01  # seconds between two looks at the pseudo console when nothing happens
DRAIN_QUIET = 0.2  # seconds without output after the end of the program before CLOSED
INPUT_QUEUE_SIZE = 256


class PseudoConsole(Protocol):
    """What the pump uses of a started pywinpty ``PTY`` (the library has no type information)."""

    @property
    def pid(self) -> int: ...

    def isalive(self) -> bool: ...

    def get_exitstatus(self) -> object:
        """The exit code; the transport takes it only if it is an ``int``."""
        ...

    def set_size(self, cols: int, rows: int) -> object: ...

    def write(self, data: str) -> object: ...

    def read(self, *, blocking: bool) -> object: ...


@dataclass(slots=True, frozen=True)
class ConPtyLaunch:
    """What to start, and the size of the pseudo console (the same as the pyte screen)."""

    arguments: tuple[str, ...]
    working_folder: Path
    environment: Mapping[str, str] | None = None  # None: inherited from MiTerm-N5
    columns: int = DEFAULT_COLUMNS
    rows: int = DEFAULT_ROWS


class ConPtyTransport:
    """Runs one program in a pseudo console: one stream, which carries VT sequences."""

    def __init__(self, launch: ConPtyLaunch) -> None:
        self._launch = launch
        self._state = TransportState.CLOSED
        self._lock = threading.Lock()
        self._listener: TransportListener | None = None
        self._pid: int | None = None
        self._tree: ProcessTree | None = None
        self._input: queue.Queue[str] = queue.Queue(INPUT_QUEUE_SIZE)
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._size: tuple[int, int] | None = None  # a resize the pump has not applied yet
        self._ended = threading.Event()

    @property
    def state(self) -> TransportState:
        with self._lock:
            return self._state

    def start(self, listener: TransportListener) -> None:
        if self._listener is not None:
            raise TransportError("already started")
        self._listener = listener
        self._set_state(TransportState.CONNECTING)
        try:
            pty = self._spawn()
        except LaunchError:
            self._set_state(TransportState.FAILED)
            raise
        self._pid = int(pty.pid)
        self._tree = hold_process_tree(self._pid)
        self._set_state(TransportState.CONNECTED)
        threading.Thread(target=self._pump, args=(pty,), name="conpty-pump", daemon=True).start()

    def write(self, data: bytes) -> None:
        """Send typed input; a line ends with a carriage return in a terminal, not a line feed."""
        if self.state is not TransportState.CONNECTED or self._ended.is_set():
            raise TransportClosedError
        try:
            text = self._decoder.decode(data)
        except UnicodeDecodeError as error:
            raise TransportError("input is not UTF-8") from error
        if not text:
            return
        try:
            self._input.put_nowait(text)
        except queue.Full as error:
            raise InputQueueFullError from error

    def resize(self, columns: int, rows: int) -> None:
        with self._lock:
            self._size = (columns, rows)

    def active_processes(self) -> int | None:
        """How many processes the program and what it started make; ``None`` when unknown."""
        tree = self._tree
        if tree is None:
            return None
        try:
            return tree.active_processes()
        except ProcessTreeError:
            logger.debug("Cannot count the processes", exc_info=True)
            return None

    def close(self) -> None:
        """Stop the program and the processes it started."""
        if self._pid is None or terminate_tree(self._tree) or self._ended.is_set():
            return
        try:
            os.kill(self._pid, signal.SIGTERM)
        except OSError:
            logger.debug("Program already ended", exc_info=True)

    def _spawn(self) -> PseudoConsole:
        launch = self._launch
        if not launch.arguments:
            raise LaunchError("")
        program = launch.arguments[0]
        if not launch.working_folder.is_dir():
            raise WorkingFolderError(program, str(launch.working_folder))
        search_path = launch.environment.get("PATH") if launch.environment is not None else None
        path = shutil.which(program, path=search_path)
        if path is None:
            raise ProgramNotFoundError(program)
        command_line = subprocess.list2cmdline(launch.arguments[1:])
        hold_foreground(Win32Foreground())  # the console window must not take the foreground
        try:
            pty = winpty.PTY(launch.columns, launch.rows, backend=winpty.Backend.ConPTY)
            started = pty.spawn(
                path,
                cmdline=f" {command_line}" if command_line else None,
                cwd=str(launch.working_folder),
                env=_environment_block(launch.environment),
            )
        except (winpty.WinptyError, OSError, ValueError) as error:
            raise LaunchError(program) from error
        if not started:
            raise LaunchError(program)
        console: PseudoConsole = pty
        return console

    def _pump(self, pty: PseudoConsole) -> None:
        """Run until the program ended and its last output was handed out."""
        listener = self._require_listener()
        quiet_since: float | None = None
        while quiet_since is None or time.monotonic() - quiet_since < DRAIN_QUIET:
            self._apply_size(pty)
            self._send_input(pty)
            text = _read(pty)
            if text:
                listener.on_data(Stream.OUTPUT, text.encode("utf-8"))
                if quiet_since is not None:
                    quiet_since = time.monotonic()
                continue
            if quiet_since is None and not pty.isalive():
                self._report_exit(pty)
                quiet_since = time.monotonic()
            time.sleep(POLL)
        if self._tree is not None:
            self._tree.close()
        # Dropping the pseudo console closes it: processes still attached to it are closed too.
        del pty
        self._set_state(TransportState.CLOSED)

    def _report_exit(self, pty: PseudoConsole) -> None:
        status = pty.get_exitstatus()
        self._ended.set()
        keep_children(self._tree)
        self._require_listener().on_exit(status if isinstance(status, int) else None)

    def _apply_size(self, pty: PseudoConsole) -> None:
        with self._lock:
            size, self._size = self._size, None
        if size is not None:
            pty.set_size(*size)

    def _send_input(self, pty: PseudoConsole) -> None:
        while not self._input.empty():
            text = self._input.get_nowait()
            try:
                pty.write(text)
            except winpty.WinptyError:
                logger.debug("Input of the program closed", exc_info=True)
                return

    def _set_state(self, state: TransportState) -> None:
        with self._lock:
            self._state = state
        self._require_listener().on_state_changed(state)

    def _require_listener(self) -> TransportListener:
        if self._listener is None:
            raise TransportError("not started")
        return self._listener


def _read(pty: PseudoConsole) -> str:
    """What the pseudo console has; empty when nothing, or when it is already closed."""
    try:
        text = pty.read(blocking=False)
    except winpty.WinptyError:
        logger.debug("Pseudo console closed", exc_info=True)
        return ""
    return str(text)


def _environment_block(environment: Mapping[str, str] | None) -> str | None:
    if environment is None:
        return None
    return "\0".join(f"{name}={value}" for name, value in environment.items()) + "\0"
