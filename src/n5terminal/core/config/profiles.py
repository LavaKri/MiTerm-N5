"""Profiles: one JSON file each, and the variables written in their commands.

See "Profiles" in ``specs/interface.md``. The name of a profile is the name of its file
(``profiles/git.json`` is the profile ``git``), so that the two can never disagree. Keys this
version does not know are kept when a profile is written again. The file of a profile that cannot be
read is set aside by ``jsonstore`` and the user is told; the other profiles are still listed.
"""

import enum
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath

from n5terminal.core.config.jsonstore import read_json, write_json
from n5terminal.core.config.settings import (
    AUTOMATIC_SIZE,
    INTERPRETERS,
    LAUNCH_MODES,
    is_valid_size,
)
from n5terminal.core.errors import JsonStoreError, ProfileError

PROFILE_SUFFIX = ".json"
MAX_NAME_LENGTH = 10
#: The variables a command can hold, in the order the interface lists them.
VARIABLES = ("name", "source", "destination", "value1", "value2", "comment", "ip", "message")

_FORBIDDEN_CHARACTERS = frozenset('<>:"/\\|?*')
_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)
_VARIABLE_PATTERN = re.compile(r"\{(" + "|".join(VARIABLES) + r")\}", re.IGNORECASE)
#: The variable of the files of older versions that is now ``comment``.
_OLD_VARIABLE = re.compile(r"\{email\}", re.IGNORECASE)


class NameProblem(enum.Enum):
    """Why a profile name is refused."""

    EMPTY = "empty"
    TOO_LONG = "too_long"
    NOT_ALLOWED = "not_allowed"  # a character outside the list of ``name_character_allowed``
    FORBIDDEN_CHARACTER = "forbidden_character"  # also a final dot or space, a reserved name
    TAKEN = "taken"  # another profile has it, the case ignored


def sorted_commands(commands: Iterable[str]) -> list[str]:
    """The common commands in alphabetical order, the case ignored (``Get-Help`` after ``dir``)."""
    return sorted(commands, key=str.casefold)


class CommandUse(enum.Enum):
    """What a common command of a profile is for (the value is what the file says).

    ``LAUNCH``: with the program in front, to start it (``git push``); the default, and what a
    command with no value in an old file is. ``PROGRAM``: typed in the program once it runs
    (``/select``). ``SHELL``: either (a command of a shell, which is complete on its own); older
    files call it ``both``.
    """

    LAUNCH = "launch"
    PROGRAM = "program"
    SHELL = "shell"


_OLD_USES = {"both": CommandUse.SHELL}


def uses_for(interpreter: str) -> tuple[CommandUse, ...]:
    """The uses a profile can give a command: only ``SHELL`` with a shell, else the other two."""
    if interpreter != "none":
        return (CommandUse.SHELL,)
    return (CommandUse.LAUNCH, CommandUse.PROGRAM)


def fit_uses(
    interpreter: str, commands: Mapping[CommandUse, list[str]]
) -> dict[CommandUse, list[str]]:
    """``commands`` with only the uses ``interpreter`` offers, losing none.

    With a shell, all the commands join ``SHELL``. Without one, the ``SHELL`` commands join both
    the launch and the program commands, where they can be typed in either state.
    """
    fitted = {use: sorted_commands(commands.get(use, [])) for use in CommandUse}
    if interpreter != "none":
        joined = {text for texts in fitted.values() for text in texts}
        return {
            CommandUse.LAUNCH: [],
            CommandUse.PROGRAM: [],
            CommandUse.SHELL: sorted_commands(joined),
        }
    shell = fitted[CommandUse.SHELL]
    fitted[CommandUse.LAUNCH] = sorted_commands({*fitted[CommandUse.LAUNCH], *shell})
    fitted[CommandUse.PROGRAM] = sorted_commands({*fitted[CommandUse.PROGRAM], *shell})
    fitted[CommandUse.SHELL] = []
    return fitted


def _read_commands(raw: object) -> dict[CommandUse, list[str]]:
    """The commands of a file by use: a text is a launch command, ``{"text", "use"}`` has its use.

    Blank texts, entries of another kind and unknown uses (they count as launch) are tolerated.
    """
    found: dict[CommandUse, list[str]] = {use: [] for use in CommandUse}
    for entry in raw if isinstance(raw, list) else []:
        text, use = entry, CommandUse.LAUNCH
        if isinstance(entry, dict):
            text = entry.get("text")
            name = entry.get("use")
            use = _OLD_USES.get(str(name)) or next(
                (u for u in CommandUse if u.value == name), CommandUse.LAUNCH
            )
        if isinstance(text, str) and text.strip():
            found[use].append(text)
    return {use: sorted_commands(texts) for use, texts in found.items()}


@dataclass(slots=True)
class Profile:
    """What a profile sets, and the commands it offers. ``variables`` are the ones it uses."""

    name: str
    launch_mode: str = "cli"
    interpreter: str = "none"
    terminal_size: str = AUTOMATIC_SIZE
    terminal_view_only: bool = False
    variables: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)  # the launch commands
    stderr_prefix: bool = True
    program: str = ""  # the program the commands are for: a name or a path, empty for none
    prompt_prefix: str = ""  # written before the prompt of a shell that stays open (``# ``)
    program_commands: list[str] = field(default_factory=list)  # typed in the program once it runs
    shell_commands: list[str] = field(default_factory=list)  # complete commands of a shell
    extra: dict[str, object] = field(default_factory=dict)  # unknown keys of the file

    def commands_of(self, use: CommandUse) -> list[str]:
        """The commands of that use."""
        return {
            CommandUse.LAUNCH: self.commands,
            CommandUse.PROGRAM: self.program_commands,
            CommandUse.SHELL: self.shell_commands,
        }[use]

    def fit_uses(self) -> None:
        """Give each command a use the profile can offer (see :func:`fit_uses`)."""
        fitted = fit_uses(self.interpreter, {use: self.commands_of(use) for use in CommandUse})
        self.commands = fitted[CommandUse.LAUNCH]
        self.program_commands = fitted[CommandUse.PROGRAM]
        self.shell_commands = fitted[CommandUse.SHELL]

    def _commands_data(self) -> list[object]:
        """The commands as the file has them, in alphabetical order: a text for a launch command
        (so that the file of an older version reads the same), else ``{"text", "use"}``."""
        entries = [(text, use) for use in CommandUse for text in self.commands_of(use)]
        entries.sort(key=lambda entry: entry[0].casefold())
        return [
            text if use is CommandUse.LAUNCH else {"text": text, "use": use.value}
            for text, use in entries
        ]

    def to_data(self) -> dict[str, object]:
        """The content of the file (the name is the name of the file)."""
        return {
            **self.extra,
            "program": self.program,
            "launch_mode": self.launch_mode,
            "interpreter": self.interpreter,
            "prompt_prefix": self.prompt_prefix,
            "terminal_size": self.terminal_size,
            "terminal_view_only": self.terminal_view_only,
            "stderr_prefix": self.stderr_prefix,
            "variables": self.variables,
            "commands": self._commands_data(),
        }

    @classmethod
    def from_data(cls, name: str, data: Mapping[str, object]) -> Profile:
        """A profile from the content of a file; a value of the wrong kind is ignored."""
        profile = cls(name)
        mode = data.get("launch_mode")
        if mode in LAUNCH_MODES:
            profile.launch_mode = str(mode)
        interpreter = data.get("interpreter")
        if interpreter in INTERPRETERS:
            profile.interpreter = str(interpreter)
        size = data.get("terminal_size")
        if isinstance(size, str) and is_valid_size(size):
            profile.terminal_size = size
        view_only = data.get("terminal_view_only")
        if isinstance(view_only, bool):
            profile.terminal_view_only = view_only
        prefix = data.get("stderr_prefix")
        if isinstance(prefix, bool):
            profile.stderr_prefix = prefix
        program = data.get("program")
        if isinstance(program, str):
            profile.program = program.strip()
        prompt_prefix = data.get("prompt_prefix")
        if isinstance(prompt_prefix, str):
            profile.prompt_prefix = prompt_prefix  # kept as written: its last space matters
        used = data.get("variables")
        if isinstance(used, list):
            names = {"comment" if str(u).lower() == "email" else str(u).lower() for u in used}
            profile.variables = [v for v in VARIABLES if v in names]
        by_use = _read_commands(data.get("commands"))
        by_use = {
            use: [_OLD_VARIABLE.sub("{comment}", text) for text in texts]
            for use, texts in by_use.items()
        }
        profile.commands = by_use[CommandUse.LAUNCH]
        profile.program_commands = by_use[CommandUse.PROGRAM]
        profile.shell_commands = by_use[CommandUse.SHELL]
        profile.fit_uses()
        known = {
            "program",
            "launch_mode",
            "interpreter",
            "prompt_prefix",
            "terminal_size",
            "terminal_view_only",
            "stderr_prefix",
            "variables",
            "commands",
        }
        profile.extra = {key: value for key, value in data.items() if key not in known}
        return profile


@dataclass(slots=True, frozen=True)
class ProfileList:
    """The profiles found, by name, and what to tell the user about the files that went wrong."""

    profiles: list[Profile]
    warnings: list[str]


#: The signs a profile name may hold besides letters, digits and spaces.
NAME_SIGNS = "-_.+#()@"


def name_character_allowed(character: str) -> bool:
    """Is ``character`` one a profile name may hold: a letter or a digit (of any language), a space
    or one of ``NAME_SIGNS``? Nothing invisible or hard to hear is."""
    return character.isalnum() or character == " " or character in NAME_SIGNS


def first_disallowed_character(name: str) -> str | None:
    """The first character of ``name`` a profile name may not hold, ``None`` if there is none."""
    return next((c for c in name if not name_character_allowed(c)), None)


def name_problem(
    name: str,
    taken: list[str],
    current: str | None = None,
    max_length: int = MAX_NAME_LENGTH,
    strict: bool = False,
) -> NameProblem | None:
    """Why ``name`` cannot name a profile (or another file of the application), ``None`` if it can.

    ``taken`` are the names that exist; ``current`` is the one being edited, whose own name does
    not count as taken. ``strict`` limits the characters to those of ``name_character_allowed``.
    """
    if not name.strip():
        return NameProblem.EMPTY
    if len(name) > max_length:
        return NameProblem.TOO_LONG
    if strict and first_disallowed_character(name) is not None:
        return NameProblem.NOT_ALLOWED
    if (
        any(c in _FORBIDDEN_CHARACTERS or ord(c) < 32 for c in name)
        or name != name.strip()
        or name.endswith(".")
        or name.split(".")[0].casefold() in _RESERVED_NAMES
    ):
        return NameProblem.FORBIDDEN_CHARACTER
    others = {t.casefold() for t in taken if current is None or t.casefold() != current.casefold()}
    return NameProblem.TAKEN if name.casefold() in others else None


def expand_variables(command: str, values: Mapping[str, str]) -> str:
    """``command`` with each ``{variable}`` that has a (non-empty) value replaced by it.

    The names are matched whatever their case. A variable without a value stays as it is, and so
    does any other brace.
    """

    def replace(match: re.Match[str]) -> str:
        return values.get(match.group(1).lower()) or match.group(0)

    return _VARIABLE_PATTERN.sub(replace, command)


def program_name(program: str) -> str:
    """The name of a program as it is said: no folder, no extension (``Git.exe`` is ``Git``)."""
    return PureWindowsPath(program.strip().strip('"')).stem


def full_command(program: str, command: str) -> str:
    """The command line to write for a common ``command`` of a profile with ``program``.

    The program is written as the profile has it, between quotes when it holds a space; a profile
    with no program has complete commands.
    """
    program = program.strip()
    if not program:
        return command
    if " " in program and not program.startswith('"'):
        program = f'"{program}"'
    return f"{program} {command}"


class ProfileStore:
    """The profile files of a folder."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def _path(self, name: str) -> Path:
        return self._folder / f"{name}{PROFILE_SUFFIX}"

    def load_all(self) -> ProfileList:
        """Every readable profile, by name; the folder not existing yet means no profile."""
        profiles: list[Profile] = []
        warnings: list[str] = []
        try:
            paths = sorted(self._folder.glob(f"*{PROFILE_SUFFIX}")) if self._folder.is_dir() else []
        except OSError as error:
            return ProfileList([], [f"Cannot list {self._folder}: {error}."])
        for path in paths:
            result = read_json(path)
            if result.warning:
                warnings.append(result.warning)
            if result.data is not None:
                profiles.append(Profile.from_data(path.stem, result.data))
        profiles.sort(key=lambda profile: profile.name.casefold())
        return ProfileList(profiles, warnings)

    def save(self, profile: Profile, replaces: str | None = None) -> None:
        """Write ``profile``; ``replaces`` is its former name when it was renamed.

        Raises ``ProfileError`` if a file cannot be written or the former one removed.
        """
        try:
            write_json(self._path(profile.name), profile.to_data())
        except JsonStoreError as error:
            raise ProfileError(str(error)) from error
        if replaces is not None and replaces.casefold() != profile.name.casefold():
            self.delete(replaces)

    def delete(self, name: str) -> None:
        """Remove the file of a profile and its backup. Raises ``ProfileError``."""
        path = self._path(name)
        try:
            path.unlink(missing_ok=True)
            path.with_name(path.name + ".bak").unlink(missing_ok=True)
        except OSError as error:
            raise ProfileError(f"Cannot delete {path}: {error}") from error
