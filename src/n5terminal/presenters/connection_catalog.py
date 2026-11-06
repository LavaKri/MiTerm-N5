"""The connections on disk, as the window uses them: the names for the menu, one connection by name.

The files are read again each time the menu opens, so a connection added or edited by hand shows at
once. Nothing here knows about ``wx``.
"""

from n5terminal.core.config.connections import Connection, ConnectionList, ConnectionStore


class ConnectionCatalog:
    """The connections of a store (``None``: there is no folder for connections, so none)."""

    def __init__(self, store: ConnectionStore | None) -> None:
        self._store = store
        loaded = store.load_all() if store is not None else ConnectionList([], [])
        self._connections = loaded.connections
        self.warnings = loaded.warnings  # the files that could not be read or used, to show once

    @property
    def writable(self) -> bool:
        """Can a connection be saved or deleted?"""
        return self._store is not None

    def names(self) -> list[str]:
        """The names of the connections on disk now (the files are read again)."""
        self.reload()
        return [connection.name for connection in self._connections]

    def reload(self) -> None:
        """Read the files again."""
        if self._store is not None:
            self._connections = self._store.load_all().connections

    def get(self, name: str) -> Connection | None:
        """The connection called ``name`` as of the last reading."""
        return next((c for c in self._connections if c.name == name), None)

    def find(self, name: str) -> Connection | None:
        """The connection called ``name`` whatever the case, as of the last reading."""
        key = name.casefold()
        return next((c for c in self._connections if c.name.casefold() == key), None)

    def save(self, connection: Connection, replaces: str | None) -> None:
        """Write ``connection`` (``replaces``: its former name). Raises ``ConnectionFileError``."""
        if self._store is not None:
            self._store.save(connection, replaces)

    def delete(self, name: str) -> None:
        """Remove the connection ``name``. Raises ``ConnectionFileError``."""
        if self._store is not None:
            self._store.delete(name)
