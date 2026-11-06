"""The diagnostic log of the application (see "Logs" in ``specs/robustness.md``).

A rotating file (5 files of 1 MB), no console. If the folder cannot be written (a USB key locked
against writing) nothing is logged: the log never goes to another place, least of all to the disk
of a host PC. What the user typed, what the programs print and the arguments of the commands never
enter the log (the arguments only at the ``DEBUG`` level).
"""

import faulthandler
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import IO

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
DEFAULT_LEVEL = "INFO"
DEVELOP_LEVEL = "DEBUG"  # the default level of the develop mode
MAX_BYTES = 1_000_000
FILE_COUNT = 5  # the current file and four older ones
FAULT_FILE = "faulthandler.log"  # beside the log, in develop mode

logger = logging.getLogger("n5terminal")
_fault_log: IO[str] | None = None  # kept open: ``faulthandler`` writes to it when the process dies


def configure_logging(log_file: Path, level: str = DEFAULT_LEVEL) -> bool:
    """Start logging to ``log_file`` at ``level``; whether the file could be opened."""
    opened = True
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            log_file, maxBytes=MAX_BYTES, backupCount=FILE_COUNT - 1, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()
        opened = False
    logging.basicConfig(
        handlers=[handler],
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )

    def log_uncaught(
        kind: type[BaseException], error: BaseException, trace: TracebackType | None
    ) -> None:
        logger.critical("Uncaught error", exc_info=(kind, error, trace))

    sys.excepthook = log_uncaught
    return opened


def enable_fault_log(log_file: Path) -> bool:
    """Write the Python stack of every thread to ``faulthandler.log``, beside ``log_file``, when
    the process dies of a native error (develop mode; whether the file could be opened).

    Such an end raises no Python exception, so the log of the application says nothing of it. The
    file holds stacks of functions and files, never the values (nothing typed or printed). It is
    started again when it passes ``MAX_BYTES``. While a screen reader runs, Windows also reports
    harmless errors that it handles itself (``0x8001010d``): this is why it is not kept for users.
    """
    global _fault_log
    path = log_file.with_name(FAULT_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if path.exists() and path.stat().st_size > MAX_BYTES else "a"
        stream = path.open(mode, encoding="utf-8")
    except OSError:
        return False
    stream.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} start ---" + chr(10))
    stream.flush()
    _fault_log = stream  # a reference must stay: faulthandler only keeps the descriptor
    faulthandler.enable(stream, all_threads=True)
    return True
