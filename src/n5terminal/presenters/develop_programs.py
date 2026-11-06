"""The test programs of the develop mode: which ones there are and how one is launched.

They are Python scripts in the ``testprograms`` folder of the develop folder. A file whose name
starts with an underscore is a helper of the programs, not a program.
"""

import sys
from pathlib import Path

TEST_PROGRAMS_FOLDER = "testprograms"  # in the DevelopMode folder


def list_test_programs(develop_folder: Path | None) -> list[Path]:
    """The test programs, by name; none outside the develop mode."""
    if develop_folder is None:
        return []
    found = (develop_folder / TEST_PROGRAMS_FOLDER).glob("*.py")
    return sorted(path for path in found if not path.name.startswith("_"))


def python_for_programs(executable: str = sys.executable) -> Path:
    """The Python that runs a test program: the one that runs the application, with a console.

    The application runs under ``pythonw.exe`` (no console); a program started with it has no
    input or output either and ends at once, so ``python.exe`` beside it is used.
    """
    path = Path(executable)
    return path.with_name("python.exe") if path.name.lower() == "pythonw.exe" else path


def program_command(program: Path, executable: str = sys.executable) -> str:
    """The command line that launches ``program``, as the user would have typed it."""
    return f'"{python_for_programs(executable)}" "{program}"'
