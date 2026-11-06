import faulthandler
import logging
import sys
from collections.abc import Iterator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from n5terminal.core.config import logging_setup
from n5terminal.core.config.logging_setup import (
    FAULT_FILE,
    FILE_COUNT,
    MAX_BYTES,
    configure_logging,
    enable_fault_log,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root, hook = logging.getLogger(), sys.excepthook
    handlers, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.handlers, root.level = handlers, level
    sys.excepthook = hook


def test_the_log_is_a_rotating_file_of_five_megabyte_files(tmp_path: Path) -> None:
    assert configure_logging(tmp_path / "logs" / "n5.log")
    [handler] = logging.getLogger().handlers
    assert isinstance(handler, RotatingFileHandler)
    assert (handler.maxBytes, handler.backupCount) == (MAX_BYTES, FILE_COUNT - 1)


def test_the_level_decides_what_is_kept(tmp_path: Path) -> None:
    log = tmp_path / "n5.log"
    configure_logging(log, "WARNING")
    logging.getLogger("n5terminal").info("not kept")
    logging.getLogger("n5terminal").warning("kept")
    configure_logging(log, "INFO")
    logging.getLogger("n5terminal").info("kept at info")
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = log.read_text(encoding="utf-8")
    assert "kept at info" in text
    assert "not kept" not in text
    assert "WARNING n5terminal kept" in text


def test_an_uncaught_error_is_logged_with_its_trace(tmp_path: Path) -> None:
    log = tmp_path / "n5.log"
    configure_logging(log)
    error = ValueError("boom")
    sys.excepthook(ValueError, error, error.__traceback__)
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "ValueError: boom" in log.read_text(encoding="utf-8")


def test_a_folder_that_cannot_be_written_means_no_log_at_all(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file", encoding="utf-8")
    assert not configure_logging(blocker / "logs" / "n5.log")
    [handler] = logging.getLogger().handlers
    assert isinstance(handler, logging.NullHandler)


def test_the_fault_log_is_a_file_beside_the_log_that_faulthandler_writes_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    enabled: list[object] = []
    monkeypatch.setattr(faulthandler, "enable", lambda *a, **k: enabled.append(a[0]))
    assert enable_fault_log(tmp_path / "logs" / "n5.log")
    path = tmp_path / "logs" / FAULT_FILE
    assert path.is_file()
    assert " start ---" in path.read_text(encoding="utf-8")
    assert len(enabled) == 1
    assert enabled[0] is logging_setup._fault_log


def test_the_fault_log_is_kept_between_starts_and_started_again_when_too_big(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(faulthandler, "enable", lambda *a, **k: None)
    path = tmp_path / FAULT_FILE
    enable_fault_log(tmp_path / "n5.log")
    enable_fault_log(tmp_path / "n5.log")
    assert path.read_text(encoding="utf-8").count(" start ---") == 2
    path.write_text("x" * (MAX_BYTES + 1), encoding="utf-8")
    enable_fault_log(tmp_path / "n5.log")
    assert path.read_text(encoding="utf-8").count(" start ---") == 1


def test_a_folder_that_cannot_be_written_means_no_fault_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    enabled: list[object] = []
    monkeypatch.setattr(faulthandler, "enable", lambda *a, **k: enabled.append(a))
    blocker = tmp_path / "blocker"
    blocker.write_text("a file", encoding="utf-8")
    assert not enable_fault_log(blocker / "logs" / "n5.log")
    assert enabled == []
