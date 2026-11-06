"""The shells that can stay open under a terminal, and the commands typed into them.

See "Interpreter" in ``specs/interface.md``: with "Cmd" or "PowerShell" a shell is started once and
every command is typed into it; this is the only case where ``cd`` has a lasting effect.
"""

import os
from collections.abc import Mapping
from pathlib import Path

from n5terminal.core.session.session_state import Interpreter

_SHELLS: dict[Interpreter, tuple[str, ...]] = {
    Interpreter.CMD: ("cmd.exe",),
    Interpreter.POWERSHELL: ("powershell.exe", "-NoLogo"),
}
_CMD_DEFAULT_PROMPT = "$P$G"


def shell_command(
    interpreter: Interpreter, prompt_prefix: str = "", powershell_path: str = ""
) -> tuple[str, ...] | None:
    """The program and arguments of the shell, ``None`` for a direct launch.

    ``powershell_path`` is the PowerShell the user chose (empty: Windows PowerShell).

    A ``prompt_prefix`` is put in front of the prompt of PowerShell, whatever the user made of it:
    the function ``prompt`` that exists after the profile of the user is called by ours, in this
    session only (nothing is written on the computer). Cmd takes it through its environment, see
    :func:`shell_environment`.
    """
    command = _SHELLS.get(interpreter)
    if command is None or interpreter is not Interpreter.POWERSHELL:
        return command
    if powershell_path.strip():
        command = (powershell_path.strip().strip('"'), *command[1:])
    if not prompt_prefix:
        return command
    quoted = prompt_prefix.replace("'", "''")
    script = f"$n5prompt = $function:prompt; function prompt {{ '{quoted}' + (& $n5prompt) }}"
    return (*command, "-NoExit", "-Command", script)


def shell_environment(
    interpreter: Interpreter, prompt_prefix: str, inherited: Mapping[str, str] | None = None
) -> dict[str, str] | None:
    """The environment of the shell, ``None`` to inherit ours as it is.

    Cmd reads its prompt in the variable ``PROMPT``: the prefix goes before the value the user
    has (``$P$G`` when there is none), for this process only.
    """
    if interpreter is not Interpreter.CMD or not prompt_prefix:
        return None
    environment = dict(os.environ if inherited is None else inherited)
    environment["PROMPT"] = prompt_prefix + environment.get("PROMPT", _CMD_DEFAULT_PROMPT)
    return environment


def change_folder_command(interpreter: Interpreter, folder: Path) -> str | None:
    """The line to type in the shell to go to ``folder`` at once, whatever its depth.

    ``cd /d`` for Cmd, so that the drive changes too; ``Set-Location -LiteralPath`` for
    PowerShell, so that ``[``, ``]`` and ``*`` are not read as wildcards. ``None`` without a
    shell. A folder name cannot hold a double quote on Windows. Known limit: Cmd still expands
    ``%name%`` inside quotes.
    """
    if interpreter is Interpreter.CMD:
        return f'cd /d "{folder}"'
    if interpreter is Interpreter.POWERSHELL:
        quoted = str(folder).replace("'", "''")
        return f"Set-Location -LiteralPath '{quoted}'"
    return None
