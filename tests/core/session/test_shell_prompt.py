import pytest

from n5terminal.core.session.session_state import Interpreter
from n5terminal.core.session.shell_prompt import at_prompt, looks_like_prompt

pytestmark = pytest.mark.unit

CMD = Interpreter.CMD
POWERSHELL = Interpreter.POWERSHELL


@pytest.mark.parametrize(
    ("interpreter", "line", "expected"),
    [
        (CMD, r"C:\Users\Codeur\Dev\Terminal>", True),
        (CMD, r"D:\>", True),
        (CMD, r"\\server\share\folder>", True),
        (CMD, "Appuyez sur une touche pour continuer...", False),  # pause
        (CMD, "Name:", False),  # set /p
        (CMD, "", False),
        (CMD, r"PS C:\Users>", False),
        (POWERSHELL, r"PS C:\Users\Codeur\Dev\Terminal>", True),
        (POWERSHELL, "Name:", False),  # Read-Host
        (POWERSHELL, "", False),  # Start-Sleep
        (POWERSHELL, r"C:\Users>", False),
        (Interpreter.NONE, r"C:\Users>", False),
    ],
)
def test_the_prompt_of_each_shell(interpreter: Interpreter, line: str, expected: bool) -> None:
    assert looks_like_prompt(interpreter, line) is expected


def test_trailing_blanks_do_not_matter() -> None:
    assert looks_like_prompt(CMD, "C:\\work>   ")


@pytest.mark.parametrize(
    ("interpreter", "line", "expected"),
    [
        (CMD, r"# C:\work>", True),
        (CMD, r"C:\work>", False),  # the prefix was asked for and is not there
        (CMD, "# Name:", False),
        (POWERSHELL, r"# PS C:\work>", True),
        (POWERSHELL, r"PS C:\work>", False),
    ],
)
def test_the_prompt_starts_with_the_prefix(
    interpreter: Interpreter, line: str, expected: bool
) -> None:
    assert looks_like_prompt(interpreter, line, "# ") is expected
    assert at_prompt(interpreter, 1, line, "# ") is expected


@pytest.mark.parametrize(
    ("processes", "line", "expected"),
    [
        (1, r"C:\work>", True),  # at the prompt
        (2, r"C:\work>", False),  # a program runs and left the old prompt on screen
        (3, "", False),  # python waiting for a line
        (1, "Appuyez sur une touche pour continuer...", False),  # pause: no process, no prompt
        (1, "Name:", False),  # set /p
        (None, r"C:\work>", False),  # no job: unknown means busy
        (0, r"C:\work>", False),  # the shell is gone
    ],
)
def test_both_signals_must_agree(processes: int | None, line: str, expected: bool) -> None:
    assert at_prompt(CMD, processes, line) is expected
