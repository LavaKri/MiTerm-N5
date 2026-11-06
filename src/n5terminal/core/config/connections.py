"""Connections: one JSON file each, saying where a session runs (here, or on an SSH server).

See "The connection file" in ``specs/architecture/connection.md``. The name of a connection is the
name of its file (``connections/prod.json`` is the connection ``prod``). A file holds no secret: no
password, no passphrase, no key. Keys this version does not know are kept when a connection is
written again. The file of a connection that cannot be read is set aside by ``jsonstore`` and the
user is told; the other connections are still listed.

The target is given to ``ssh`` as an argument of its own, so it is checked before anything is
launched (``target_problem``): ``ssh`` would take a target that starts with a dash for an option.
"""

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from n5terminal.core.config.jsonstore import read_json, write_json
from n5terminal.core.config.profiles import NameProblem, name_problem
from n5terminal.core.errors import ConnectionFileError, JsonStoreError

CONNECTION_SUFFIX = ".json"
MAX_NAME_LENGTH = 20
MIN_PORT = 1
MAX_PORT = 65535


class TargetProblem(enum.Enum):
    """Why the target of a connection is refused."""

    EMPTY = "empty"  # also nothing after the @
    OPTION_LIKE = "option_like"  # a dash starts the target, or the host after the @
    FORBIDDEN_CHARACTER = "forbidden_character"  # a space or other blank, a control character


def target_problem(target: str) -> TargetProblem | None:
    """Why ``target`` cannot be given to ``ssh``, ``None`` if it can.

    A target is an alias of the ``~/.ssh/config`` of the user, or ``user@host``.
    """
    if not target.strip():
        return TargetProblem.EMPTY
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in target):
        return TargetProblem.FORBIDDEN_CHARACTER
    host = target.rpartition("@")[2]
    if not host:
        return TargetProblem.EMPTY
    if target.startswith("-") or host.startswith("-"):
        return TargetProblem.OPTION_LIKE
    return None


def is_valid_port(port: object) -> bool:
    """Is ``port`` a whole number from 1 to 65535? (A boolean is not.)"""
    return isinstance(port, int) and not isinstance(port, bool) and MIN_PORT <= port <= MAX_PORT


def connection_name_problem(
    name: str, taken: list[str], current: str | None = None, strict: bool = False
) -> NameProblem | None:
    """Why ``name`` cannot name a connection, ``None`` if it can (see ``name_problem``).

    ``strict`` limits the characters to those of a profile name.
    """
    return name_problem(name, taken, current, max_length=MAX_NAME_LENGTH, strict=strict)


@dataclass(slots=True)
class Connection:
    """Where a session runs: the ``target`` (an alias or ``user@host``), the ``port`` if it is not
    the one ``ssh`` finds. It has no profile: a profile of a program is chosen on its own."""

    name: str
    target: str = ""
    port: int | None = None
    extra: dict[str, object] = field(default_factory=dict)  # unknown keys of the file

    def to_data(self) -> dict[str, object]:
        """The content of the file (the name is the name of the file)."""
        return {**self.extra, "target": self.target, "port": self.port}

    @classmethod
    def from_data(cls, name: str, data: Mapping[str, object]) -> Connection:
        """A connection from the content of a file; a value of the wrong kind is ignored."""
        connection = cls(name)
        target = data.get("target")
        if isinstance(target, str):
            connection.target = target.strip()
        port = data.get("port")
        if isinstance(port, int) and is_valid_port(port):
            connection.port = port
        known = {"target", "port"}  # a "profile" of an older version is kept as an unknown key
        connection.extra = {key: value for key, value in data.items() if key not in known}
        return connection


@dataclass(slots=True, frozen=True)
class ConnectionList:
    """The connections found, by name, and what to tell the user about the files that went wrong."""

    connections: list[Connection]
    warnings: list[str]


class ConnectionStore:
    """The connection files of a folder."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def _path(self, name: str) -> Path:
        return self._folder / f"{name}{CONNECTION_SUFFIX}"

    def load_all(self) -> ConnectionList:
        """Every readable connection, by name; the folder not existing yet means no connection.

        A connection whose target cannot be used is listed, so that the user can correct it, and
        reported in the warnings.
        """
        connections: list[Connection] = []
        warnings: list[str] = []
        try:
            paths = (
                sorted(self._folder.glob(f"*{CONNECTION_SUFFIX}")) if self._folder.is_dir() else []
            )
        except OSError as error:
            return ConnectionList([], [f"Cannot list {self._folder}: {error}."])
        for path in paths:
            result = read_json(path)
            if result.warning:
                warnings.append(result.warning)
            if result.data is None:
                continue
            connection = Connection.from_data(path.stem, result.data)
            problem = target_problem(connection.target)
            if problem is not None:
                warnings.append(
                    f"The target of the connection {connection.name} cannot be used"
                    f" ({problem.value}): correct it before connecting."
                )
            connections.append(connection)
        connections.sort(key=lambda connection: connection.name.casefold())
        return ConnectionList(connections, warnings)

    def save(self, connection: Connection, replaces: str | None = None) -> None:
        """Write ``connection``; ``replaces`` is its former name when it was renamed.

        Raises ``ConnectionFileError`` if a file cannot be written or the former one removed.
        """
        try:
            write_json(self._path(connection.name), connection.to_data())
        except JsonStoreError as error:
            raise ConnectionFileError(str(error)) from error
        if replaces is not None and replaces.casefold() != connection.name.casefold():
            self.delete(replaces)

    def delete(self, name: str) -> None:
        """Remove the file of a connection and its backup. Raises ``ConnectionFileError``."""
        path = self._path(name)
        try:
            path.unlink(missing_ok=True)
            path.with_name(path.name + ".bak").unlink(missing_ok=True)
        except OSError as error:
            raise ConnectionFileError(f"Cannot delete {path}: {error}") from error
