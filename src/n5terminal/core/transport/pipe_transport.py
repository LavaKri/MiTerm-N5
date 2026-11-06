"""Local transport through pipes: the CLI modes 1 to 3 (see ``specs/architecture/transport.md``).

The program is started directly, without a shell. One thread reads stdout, one reads stderr, one
writes the input from a bounded queue, and one waits for the end of the program.
"""

import logging
import queue
import subprocess
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from n5terminal.core.errors import (
    InputQueueFullError,
    LaunchError,
    ProgramNotFoundError,
    TransportClosedError,
    TransportError,
    WorkingFolderError,
)
from n5terminal.core.transport.process_tree import (
    ProcessTree,
    hold_process_tree,
    keep_children,
    terminate_tree,
)
from n5terminal.core.transport.transport import Stream, TransportListener, TransportState

logger = logging.getLogger(__name__)

READ_SIZE = 65536
INPUT_QUEUE_SIZE = 256
STOP_TIMEOUT = 2.0  # seconds a program has to stop before it is killed
INPUT_POLL = 0.1  # seconds between two checks of the end of the program by the input thread
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(slots=True, frozen=True)
class PipeLaunch:
    """What to start. Local notions stay here, out of the ``Transport`` contract."""

    arguments: tuple[str, ...]
    working_folder: Path
    environment: Mapping[str, str] | None = None  # None: inherited from MiTerm-N5


class PipeTransport:
    """Runs one program with its stdin, stdout and stderr connected to pipes."""

    def __init__(self, launch: PipeLaunch) -> None:
        self._launch = launch
        self._state = TransportState.CLOSED
        self._lock = threading.Lock()
        self._listener: TransportListener | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._tree: ProcessTree | None = None
        self._input: queue.Queue[bytes] = queue.Queue(INPUT_QUEUE_SIZE)
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
            process = self._spawn()
        except LaunchError:
            self._set_state(TransportState.FAILED)
            raise
        self._process = process
        self._tree = hold_process_tree(process.pid)
        self._set_state(TransportState.CONNECTED)
        stdout, stderr, stdin = _pipes(process)
        readers = [
            _start_thread("stdout", self._read, stdout, Stream.OUTPUT),
            _start_thread("stderr", self._read, stderr, Stream.ERROR),
        ]
        _start_thread("stdin", self._write_input, stdin)
        _start_thread("watch", self._watch, process, readers)

    def write(self, data: bytes) -> None:
        if self.state is not TransportState.CONNECTED or self._ended.is_set():
            raise TransportClosedError
        try:
            self._input.put_nowait(data)
        except queue.Full as error:
            raise InputQueueFullError from error

    def resize(self, columns: int, rows: int) -> None:
        """Pipes have no screen: nothing to do."""

    def close(self) -> None:
        """Stop the program and the processes it started, even if the program itself ended."""
        process = self._process
        if process is None or terminate_tree(self._tree):
            return
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.warning("Program did not stop, killing it")
            process.kill()

    def _spawn(self) -> subprocess.Popen[bytes]:
        launch = self._launch
        if not launch.arguments:
            raise LaunchError("")
        program = launch.arguments[0]
        if not launch.working_folder.is_dir():
            raise WorkingFolderError(program, str(launch.working_folder))
        environment = dict(launch.environment) if launch.environment is not None else None
        try:
            return subprocess.Popen(
                list(launch.arguments),
                cwd=launch.working_folder,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                creationflags=_NO_WINDOW,
            )
        except FileNotFoundError as error:
            raise ProgramNotFoundError(program) from error
        except (OSError, ValueError) as error:  # ValueError: a null character in an argument
            raise LaunchError(program) from error

    def _read(self, pipe: IO[bytes], stream: Stream) -> None:
        listener = self._require_listener()
        while chunk := pipe.read(READ_SIZE):
            listener.on_data(stream, chunk)
        pipe.close()

    def _write_input(self, pipe: IO[bytes]) -> None:
        try:
            while not self._ended.is_set():
                try:
                    data = self._input.get(timeout=INPUT_POLL)
                except queue.Empty:
                    continue
                pipe.write(data)
        except OSError:
            # The program closed its input or ended: what is left in the queue cannot be sent.
            logger.debug("Input of the program closed", exc_info=True)
        finally:
            _close_quietly(pipe)

    def _watch(self, process: subprocess.Popen[bytes], readers: list[threading.Thread]) -> None:
        """Report the end of the program, then the end of its output.

        A process the program started may hold the output pipes after the program ended: the
        transport stays connected (and stoppable) until they are closed.
        """
        exit_code = process.wait()
        self._ended.set()
        keep_children(self._tree)
        self._require_listener().on_exit(exit_code)
        for reader in readers:
            reader.join()
        if self._tree is not None:
            self._tree.close()
        self._set_state(TransportState.CLOSED)

    def _set_state(self, state: TransportState) -> None:
        with self._lock:
            self._state = state
        self._require_listener().on_state_changed(state)

    def _require_listener(self) -> TransportListener:
        if self._listener is None:
            raise TransportError("not started")
        return self._listener


def _pipes(process: subprocess.Popen[bytes]) -> tuple[IO[bytes], IO[bytes], IO[bytes]]:
    if process.stdout is None or process.stderr is None or process.stdin is None:
        raise TransportError("pipes missing")
    return process.stdout, process.stderr, process.stdin


def _start_thread(name: str, target: Callable[..., None], *arguments: object) -> threading.Thread:
    thread = threading.Thread(target=target, args=arguments, name=f"pipe-{name}", daemon=True)
    thread.start()
    return thread


def _close_quietly(pipe: IO[bytes]) -> None:
    try:
        pipe.close()
    except OSError:
        logger.debug("Input pipe already broken", exc_info=True)
