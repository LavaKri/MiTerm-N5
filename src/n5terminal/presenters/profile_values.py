"""The profile chosen for a session and the values given to the variables of the profiles.

Split from ``session_presenter.py`` (one subject per file). The values are kept by profile name for
the life of the session; the commands of the chosen profile come with them filled in.
"""

from dataclasses import dataclass

from n5terminal.core.config.profiles import (
    CommandUse,
    Profile,
    expand_variables,
    full_command,
    program_name,
)


@dataclass(slots=True, frozen=True)
class CommandEntry:
    """A line of the list of commands: what is read (``label``) and what is written (``text``)."""

    label: str
    text: str


class ProfileValues:
    """The chosen profile (``None``: the free profile) and the variable values of every profile."""

    def __init__(self) -> None:
        self._chosen: Profile | None = None
        self._values: dict[str, dict[str, str]] = {}
        # On a server a program is written by its file name: a path of Windows does not exist there.
        self.on_server = False

    def choose(self, profile: Profile | None) -> None:
        """Choose ``profile``, or ``None`` for the free profile."""
        self._chosen = profile

    def variables(self) -> list[str]:
        """The variables the chosen profile uses (empty with the free profile)."""
        return list(self._chosen.variables) if self._chosen is not None else []

    def program(self) -> str:
        """The program of the chosen profile, as the profile has it (empty: none).

        A profile with a shell has none: its commands are typed into the shell, complete.
        """
        chosen = self._chosen
        return chosen.program if chosen is not None and chosen.interpreter == "none" else ""

    def commands(self, use: CommandUse = CommandUse.LAUNCH) -> list[str]:
        """The common commands of that use of the chosen profile, the variables that have a value
        replaced."""
        if self._chosen is None:
            return []
        values = self._values.get(self._chosen.name, {})
        return [expand_variables(command, values) for command in self._chosen.commands_of(use)]

    def entries(self, running: bool = False) -> list[CommandEntry]:
        """The lines of the list of commands for the chosen profile, in the state of the session.

        With no program running: the launch commands and those for both. With a program: the
        program commands and those for both, written as they are. A launch line says the name of
        the program only (``Git status``, not the path, which is long to hear). Choosing it writes
        the command alone, the field holding the arguments of the program; on a server, where the
        field is typed to a shell, it writes the name of the program, then the command.
        """
        if self._chosen is None:
            return []
        if running:
            return [
                CommandEntry(command, command)
                for use in (CommandUse.PROGRAM, CommandUse.SHELL)
                for command in self.commands(use)
            ]
        name = program_name(self.program())
        return [
            CommandEntry(
                f"{name} {command}" if name else command,
                full_command(name, command) if self.on_server else command,
            )
            for use in (CommandUse.LAUNCH, CommandUse.SHELL)
            for command in self.commands(use)
        ]

    @property
    def takes_arguments(self) -> bool:
        """Does the command field hold the arguments of the program of the profile?

        Not on a server: the field is typed to a shell there, whole lines.
        """
        return bool(self.program()) and not self.on_server

    def arguments_of(self, line: str) -> str | None:
        """The arguments in a command line launched with the program of the chosen profile.

        ``None`` when the line is another program's.
        """
        program = self.program()
        prefix = full_command(program, "").strip()
        if line == prefix:
            return ""
        return line[len(prefix) :].strip() if line.startswith(prefix + " ") else None

    def set(self, profile: str, values: dict[str, str]) -> None:
        """The values of the variables of ``profile``, kept until the session ends."""
        self._values[profile] = dict(values)

    def get(self, profile: str) -> dict[str, str]:
        """The values of the variables of ``profile`` (empty: none given yet)."""
        return dict(self._values.get(profile, {}))

    def rename(self, old: str, new: str) -> None:
        """The profile ``old`` is now called ``new``: its values follow."""
        if old != new and old in self._values:
            self._values[new] = self._values.pop(old)

    def forget(self, profile: str) -> None:
        """The profile is deleted: its values go with it."""
        self._values.pop(profile, None)
