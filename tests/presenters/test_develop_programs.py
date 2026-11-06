from pathlib import Path

import pytest

from n5terminal.presenters.develop_programs import (
    list_test_programs,
    program_command,
    python_for_programs,
)

pytestmark = pytest.mark.unit


def test_outside_the_develop_mode_there_is_no_program() -> None:
    assert list_test_programs(None) == []


def test_the_programs_are_the_scripts_without_the_helpers(tmp_path: Path) -> None:
    folder = tmp_path / "testprograms"
    folder.mkdir()
    for name in ("Beta.py", "Alpha.py", "_common.py", "notes.txt"):
        (folder / name).write_text("", encoding="utf-8")
    assert [path.name for path in list_test_programs(tmp_path)] == ["Alpha.py", "Beta.py"]


def test_a_develop_folder_without_programs_gives_none(tmp_path: Path) -> None:
    assert list_test_programs(tmp_path) == []


def test_a_program_without_a_console_is_run_by_the_python_with_one() -> None:
    assert python_for_programs(r"C:\Python\pythonw.exe") == Path(r"C:\Python\python.exe")
    assert python_for_programs(r"C:\Python\PYTHONW.EXE") == Path(r"C:\Python\python.exe")
    assert python_for_programs(r"C:\Python\python.exe") == Path(r"C:\Python\python.exe")


def test_the_command_quotes_the_python_and_the_program() -> None:
    command = program_command(Path(r"C:\My Dev\Progress.py"), r"C:\Py thon\pythonw.exe")
    assert command == r'"C:\Py thon\python.exe" "C:\My Dev\Progress.py"'
