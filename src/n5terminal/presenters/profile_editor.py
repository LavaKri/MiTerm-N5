"""The draft of the profile dialog: what Add and Edit of the Profile menu change.

See "Profile dialog" in ``specs/interface.md``. The dialog edits this draft; ``build`` makes the
profile to write once the name is accepted. The commands are kept as typed (the variables are only
replaced when the list of Ctrl+Space is made).
"""

import unicodedata
from copy import deepcopy

from n5terminal.core.config.profiles import (
    MAX_NAME_LENGTH,
    NAME_SIGNS,
    VARIABLES,
    CommandUse,
    NameProblem,
    Profile,
    first_disallowed_character,
    fit_uses,
    name_problem,
    sorted_commands,
    uses_for,
)
from n5terminal.i18n import N_
from n5terminal.presenters.choices import (
    Choices,
    Translate,
    interpreter_choices,
    mode_choices,
    size_choices,
)

_VARIABLE_LABELS = {
    "name": N_("Name"),
    "source": N_("Source"),
    "destination": N_("Destination"),
    "value1": N_("Value 1"),
    "value2": N_("Value 2"),
    "comment": N_("Comment"),
    "ip": N_("IP address"),
    "message": N_("Message"),
}


def describe_character(character: str) -> str:
    """A character as a message writes it: itself, or its name when it cannot be seen."""
    if character.isprintable() and not character.isspace():
        return character
    return unicodedata.name(character, f"U+{ord(character):04X}").lower()


def variable_label(variable: str, translate: Translate) -> str:
    """The name of a variable in words (``Source``), as the dialogs write it."""
    return translate(_VARIABLE_LABELS[variable])


_USE_LABELS = {
    CommandUse.LAUNCH: N_("Launch command"),
    CommandUse.PROGRAM: N_("Program command"),
    CommandUse.SHELL: N_("Shell"),
}
VARIABLE_LINE = N_("{label}, {variable}")  # the label, then the text to write in a command
_PROBLEMS = {
    NameProblem.EMPTY: N_("The name cannot be empty."),
    NameProblem.TOO_LONG: N_("The name cannot be longer than {limit} characters."),
    NameProblem.FORBIDDEN_CHARACTER: N_(
        'The name cannot hold any of these characters: < > : " / \\ | ? *, '
        "nor end with a dot or a space, nor be a name reserved by Windows."
    ),
    NameProblem.NOT_ALLOWED: N_(
        "The character {character} is not allowed in a name. "
        "A name holds letters, digits, spaces and these signs: {signs}"
    ),
    NameProblem.TAKEN: N_("Another profile already has this name."),
}


class ProfileEditor:
    """The draft of one profile. ``existing`` are the names of the profiles now on disk."""

    def __init__(self, profile: Profile, existing: list[str], translate: Translate) -> None:
        self._original = deepcopy(profile)
        self._existing = existing
        self._translate = translate
        self.name = profile.name
        self.program = profile.program
        self.launch_mode = profile.launch_mode
        self._interpreter = profile.interpreter
        self.prompt_prefix = profile.prompt_prefix
        self.terminal_size = profile.terminal_size
        self.terminal_view_only = profile.terminal_view_only
        self.stderr_prefix = profile.stderr_prefix
        self.variables = list(profile.variables)
        self._lists = fit_uses(
            profile.interpreter, {use: profile.commands_of(use) for use in CommandUse}
        )
        # The list shows the commands of one use; it starts on the first use that has some.
        offered = uses_for(self._interpreter)
        self.use = next((use for use in offered if self._lists[use]), offered[0])

    @property
    def interpreter(self) -> str:
        return self._interpreter

    @interpreter.setter
    def interpreter(self, value: str) -> None:
        """Choose the shell; the commands move to the uses it offers, none is lost."""
        if value == self._interpreter:
            return
        self._interpreter = value
        self._lists = fit_uses(value, self._lists)
        offered = uses_for(value)
        if self.use not in offered:
            self.use = offered[0]

    @property
    def commands(self) -> list[str]:
        """The commands of the use now chosen, in alphabetical order (what the list shows)."""
        return self._lists[self.use]

    def use_choices(self) -> list[tuple[CommandUse, str]]:
        """The uses a command can have, with their words: they filter the list.

        A shell has only complete commands; without one, a command is for the launch or the program.
        """
        return [(use, self._translate(_USE_LABELS[use])) for use in uses_for(self._interpreter)]

    @property
    def is_new(self) -> bool:
        """Is this a profile being added (it has no name yet)?"""
        return not self._original.name

    def mode_choices(self) -> Choices:
        return mode_choices(self._translate)

    def interpreter_choices(self) -> Choices:
        return interpreter_choices(self._translate)

    def size_choices(self) -> Choices:
        return size_choices(self._translate)

    @property
    def mode_enabled(self) -> bool:
        """A shell that stays open is always a TUI: the mode only matters without one."""
        return self.interpreter == "none"

    @property
    def program_enabled(self) -> bool:
        """A shell gets complete commands typed into it: the program only matters without one."""
        return self.interpreter == "none"

    @property
    def prompt_prefix_enabled(self) -> bool:
        """The prefix of the prompt only means something for a shell that stays open."""
        return self.interpreter != "none"

    def variable_lines(self) -> list[tuple[str, str]]:
        """One (variable, line) per variable: ``Name, {name}``, no column."""
        return [
            (
                variable,
                self._translate(VARIABLE_LINE).format(
                    label=self._translate(_VARIABLE_LABELS[variable]),
                    variable="{" + variable + "}",
                ),
            )
            for variable in VARIABLES
        ]

    def set_variables(self, variables: list[str]) -> None:
        """The variables the profile uses, in the usual order; unknown names are ignored."""
        self.variables = [v for v in VARIABLES if v in variables]

    def name_message(self) -> str | None:
        """Why the name is refused, in words; ``None`` if it is fine."""
        # A name written before the list of characters existed stays valid while it is not changed.
        strict = self.is_new or self.name != self._original.name
        problem = name_problem(
            self.name, self._existing, None if self.is_new else self._original.name, strict=strict
        )
        if problem is None:
            return None
        character = first_disallowed_character(self.name) or ""
        return self._translate(_PROBLEMS[problem]).format(
            limit=MAX_NAME_LENGTH,
            character=describe_character(character),
            signs=" ".join(NAME_SIGNS),
        )

    def duplicate_index(self, command: str, skip: int | None = None) -> int | None:
        """The index of ``command`` in the list now shown (``skip`` is a line to leave out)."""
        return next(
            (i for i, other in enumerate(self.commands) if other == command and i != skip), None
        )

    def add_command(self, command: str) -> int | None:
        """Add ``command`` to the use now chosen; its index in the list.

        ``None`` if it is blank or already in the list.
        """
        if not command.strip() or self.duplicate_index(command) is not None:
            return None
        self._lists[self.use] = sorted_commands([*self.commands, command])
        return self.commands.index(command)

    def replace_command(self, index: int, command: str) -> int | None:
        """Replace the command at ``index``; its new index.

        ``None`` if refused: blank, no such line, or the same as another line.
        """
        if (
            not command.strip()
            or not 0 <= index < len(self.commands)
            or self.duplicate_index(command, skip=index) is not None
        ):
            return None
        self.commands[index] = command
        self._lists[self.use] = sorted_commands(self.commands)
        return self.commands.index(command)

    def remove_command(self, index: int) -> int | None:
        """Remove the command at ``index``; the index to select afterwards, ``None`` if none."""
        if not 0 <= index < len(self.commands):
            return None
        del self.commands[index]
        return min(index, len(self.commands) - 1) if self.commands else None

    def build(self) -> Profile:
        """The profile this draft describes (the keys of the file it does not know are kept)."""
        return Profile(
            self.name,
            launch_mode=self.launch_mode,
            interpreter=self.interpreter,
            prompt_prefix=self.prompt_prefix,
            terminal_size=self.terminal_size,
            terminal_view_only=self.terminal_view_only,
            variables=list(self.variables),
            commands=list(self._lists[CommandUse.LAUNCH]),
            program_commands=list(self._lists[CommandUse.PROGRAM]),
            shell_commands=list(self._lists[CommandUse.SHELL]),
            stderr_prefix=self.stderr_prefix,
            program=self.program.strip(),
            extra=dict(self._original.extra),
        )

    @property
    def replaces(self) -> str | None:
        """The former name of the profile, to give to ``ProfileStore.save``."""
        return None if self.is_new else self._original.name
