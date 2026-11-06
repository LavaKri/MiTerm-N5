"""Does a shell that stays open wait at its prompt? (rule found by experiment, see below)

Two signals, and **both** must agree; in doubt the shell counts as busy, which is the safe answer
(the item "Working folder" stays disabled, nothing is typed into a program that would read it):
- the Job object of the shell holds **one** process: the shell alone. A program it runs makes it
  two or more. Not enough alone: the shell's own commands that wait (``pause``, ``set /p`` in Cmd,
  ``Read-Host`` or ``Start-Sleep`` in PowerShell) start no process;
- the **line of the cursor** looks like the prompt of that shell. Those waiting commands leave
  another text there ("Name:", an empty line).

Measured with ``tools/probe_shell_prompt.py``. Known limits: a custom prompt (``prompt $G``, a
theme) is not recognised, so the shell always counts as busy; a waiting command whose own text
looks like a prompt (ends with ``>`` after a drive letter) would be taken for one.
"""

import re

from n5terminal.core.session.session_state import Interpreter

_PROMPTS = {
    Interpreter.CMD: re.compile(r"^(?:[A-Za-z]:\\|\\\\).*>$"),
    Interpreter.POWERSHELL: re.compile(r"^PS .*>$"),
}


def looks_like_prompt(interpreter: Interpreter, cursor_line: str, prompt_prefix: str = "") -> bool:
    """Is ``cursor_line`` the prompt of that shell, as it shows by default?

    With a ``prompt_prefix`` (the profile has one) the line starts with it, and the rest is the
    default prompt.
    """
    pattern = _PROMPTS.get(interpreter)
    if pattern is None or not cursor_line.startswith(prompt_prefix):
        return False
    return pattern.match(cursor_line[len(prompt_prefix) :].rstrip()) is not None


def at_prompt(
    interpreter: Interpreter, processes: int | None, cursor_line: str, prompt_prefix: str = ""
) -> bool:
    """Does the shell wait at its prompt? ``processes`` is unknown (``None``) without a job."""
    return processes == 1 and looks_like_prompt(interpreter, cursor_line, prompt_prefix)
