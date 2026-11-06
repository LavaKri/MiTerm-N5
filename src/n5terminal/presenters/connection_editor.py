"""The draft of the connection dialog: what Add and Edit of the Connection menu change.

See "Connections" in ``specs/interface.md``. The dialog edits this draft; ``build`` makes the
connection to write once everything is accepted. A connection holds a name, a target and a port
(nothing secret, and no profile). The keys of the file this version does not know are kept.
"""

import enum
from copy import deepcopy

from n5terminal.core.config.connections import (
    MAX_NAME_LENGTH,
    MAX_PORT,
    MIN_PORT,
    Connection,
    TargetProblem,
    connection_name_problem,
    is_valid_port,
    target_problem,
)
from n5terminal.core.config.profiles import NAME_SIGNS, NameProblem, first_disallowed_character
from n5terminal.i18n import N_
from n5terminal.presenters.choices import Translate
from n5terminal.presenters.profile_editor import describe_character

_NAME_PROBLEMS = {
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
    NameProblem.TAKEN: N_("Another connection already has this name."),
}
_TARGET_PROBLEMS = {
    TargetProblem.EMPTY: N_("The target cannot be empty."),
    TargetProblem.OPTION_LIKE: N_(
        "The target cannot start with a dash, nor can the server after the @."
    ),
    TargetProblem.FORBIDDEN_CHARACTER: N_("The target cannot hold a space or a control character."),
}
_PORT_PROBLEM = N_("The port is a whole number from {first} to {last}, or nothing.")


class Field(enum.Enum):
    """The fields of the dialog that can be refused, in the order they are checked."""

    NAME = "name"
    TARGET = "target"
    PORT = "port"


class ConnectionEditor:
    """The draft of one connection. ``existing`` are the names of the connections on disk."""

    def __init__(self, connection: Connection, existing: list[str], translate: Translate) -> None:
        self._original = deepcopy(connection)
        self._existing = existing
        self._translate = translate
        self.name = connection.name
        self.target = connection.target
        self.port = "" if connection.port is None else str(connection.port)

    @property
    def is_new(self) -> bool:
        """Is this a connection being added (it has no name yet)?"""
        return not self._original.name

    @property
    def replaces(self) -> str | None:
        """The name the connection had before, when it is being edited."""
        return None if self.is_new else self._original.name

    def problem(self) -> tuple[Field, str] | None:
        """The first thing refused, with the words that say why; ``None`` if all is fine."""
        for field, message in (
            (Field.NAME, self.name_message()),
            (Field.TARGET, self.target_message()),
            (Field.PORT, self.port_message()),
        ):
            if message is not None:
                return field, message
        return None

    def name_message(self) -> str | None:
        # A name written before the list of characters existed stays valid while it is not changed.
        strict = self.is_new or self.name != self._original.name
        problem = connection_name_problem(self.name, self._existing, self.replaces, strict=strict)
        if problem is None:
            return None
        character = first_disallowed_character(self.name) or ""
        return self._translate(_NAME_PROBLEMS[problem]).format(
            limit=MAX_NAME_LENGTH,
            character=describe_character(character),
            signs=" ".join(NAME_SIGNS),
        )

    def target_message(self) -> str | None:
        problem = target_problem(self.target)
        return None if problem is None else self._translate(_TARGET_PROBLEMS[problem])

    def port_message(self) -> str | None:
        if not self.port.strip() or self._port_number() is not None:
            return None
        return self._translate(_PORT_PROBLEM).format(first=MIN_PORT, last=MAX_PORT)

    def _port_number(self) -> int | None:
        text = self.port.strip()
        if not (text.isascii() and text.isdigit()):
            return None
        number = int(text)
        return number if is_valid_port(number) else None

    def build(self) -> Connection:
        """The connection this draft describes (the keys of the file it does not know are kept)."""
        return Connection(
            self.name.strip(),
            target=self.target.strip(),
            port=self._port_number(),
            extra=dict(self._original.extra),
        )
