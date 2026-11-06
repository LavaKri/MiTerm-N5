"""Where the application runs, as the main window needs to know it.

One object instead of six values handed from the entry point through the window to its actions.
Everything is optional: a window with none of it (tests) has no profile folder, no association and
no develop mode.
"""

from dataclasses import dataclass
from pathlib import Path

from n5terminal.core.config.file_association import FileAssociation
from n5terminal.core.config.location import DataLocation


@dataclass(slots=True, frozen=True)
class AppContext:
    """The folders, the file association and the data location of this run."""

    data_folder: Path | None = None  # given with --data-folder: a new session is started with it
    profiles_folder: Path | None = None
    connections_folder: Path | None = None
    association: FileAssociation | None = None  # None in portable mode: nothing is registered
    log_folder: Path | None = None
    develop_folder: Path | None = None  # the DevelopMode folder when run with --develop
    location: DataLocation | None = None
    help_folder: Path | None = None  # the Help folder beside the application

    @classmethod
    def from_location(
        cls,
        location: DataLocation,
        association: FileAssociation | None,
        help_folder: Path | None = None,
    ) -> AppContext:
        """The context of a run whose data lives in ``location``."""
        return cls(
            help_folder=help_folder,
            data_folder=location.explicit_folder,
            profiles_folder=location.profiles_folder,
            connections_folder=location.connections_folder,
            association=association,
            log_folder=location.log_file.parent,
            develop_folder=location.settings_file.parent if location.develop else None,
            location=location,
        )
