"""The profiles on disk, as the window uses them: the names for the menu, one profile by name.

The files are read again each time the menu opens, so a profile added or edited by hand shows at
once. Nothing here knows about ``wx``.
"""

from n5terminal.core.config.profiles import Profile, ProfileList, ProfileStore


class ProfileCatalog:
    """The profiles of a store (``None``: there is no folder for profiles, so none)."""

    def __init__(self, store: ProfileStore | None) -> None:
        self._store = store
        loaded = store.load_all() if store is not None else ProfileList([], [])
        self._profiles = loaded.profiles
        self.warnings = loaded.warnings  # the files that could not be read, to show once

    @property
    def writable(self) -> bool:
        """Can a profile be saved or deleted?"""
        return self._store is not None

    def names(self) -> list[str]:
        """The names of the profiles on disk now (the files are read again)."""
        self.reload()
        return [profile.name for profile in self._profiles]

    def reload(self) -> None:
        """Read the files again."""
        if self._store is not None:
            self._profiles = self._store.load_all().profiles

    def get(self, name: str) -> Profile | None:
        """The profile called ``name`` as of the last reading."""
        return next((profile for profile in self._profiles if profile.name == name), None)

    def find(self, name: str) -> Profile | None:
        """The profile called ``name`` whatever the case, as of the last reading."""
        key = name.casefold()
        return next((profile for profile in self._profiles if profile.name.casefold() == key), None)

    def save(self, profile: Profile, replaces: str | None) -> None:
        """Write ``profile`` (``replaces``: its former name). Raises ``ProfileError``."""
        if self._store is not None:
            self._store.save(profile, replaces)

    def delete(self, name: str) -> None:
        """Remove the profile ``name``. Raises ``ProfileError``."""
        if self._store is not None:
            self._store.delete(name)
