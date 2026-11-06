"""Where the data of the application lives: in the profile of the user, or beside the program.

See "Where the data lives" in ``specs/architecture/window.md``.

Three ways of working. Local: the settings and the profiles are in the profile of the Windows user
(roaming), the logs in the local data folder. Portable: everything is in a folder of the
application, so that a USB key leaves nothing on the host. Portable is chosen by a file named
``portable`` beside the program, or by ``--data-folder``, which wins. Develop (``--develop``) wins
over both: see ``develop_location``.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

from n5terminal.core.config.packaged import is_packaged
from n5terminal.core.config.settings import SETTINGS_FILE_NAME
from n5terminal.core.config.starter_profiles import STARTER_FOLDER

APP_NAME = "MiTerm-N5"
MARKER_FILE = "portable"
PORTABLE_FOLDER = "data"
DEVELOP_FOLDER = "DevelopMode"
PROFILES_FOLDER = "profiles"
CONNECTIONS_FOLDER = "connections"
LOG_FILE_NAME = "n5terminal.log"


@dataclass(slots=True, frozen=True)
class DataLocation:
    """The files of the application. ``explicit_folder`` is the one given with ``--data-folder``."""

    settings_file: Path
    profiles_folder: Path
    connections_folder: Path
    log_file: Path
    portable: bool
    explicit_folder: Path | None = None
    develop: bool = False


def local_location() -> DataLocation:
    """The profile of the Windows user: settings and profiles roaming, logs local."""
    config = Path(user_config_dir(APP_NAME, appauthor=False, roaming=True))
    logs = Path(user_log_dir(APP_NAME, appauthor=False))
    return DataLocation(
        settings_file=config / SETTINGS_FILE_NAME,
        profiles_folder=config / PROFILES_FOLDER,
        connections_folder=config / CONNECTIONS_FOLDER,
        log_file=logs / LOG_FILE_NAME,
        portable=False,
    )


def portable_location(data_folder: Path, explicit: bool = False) -> DataLocation:
    """Everything in ``data_folder``: ``settings.json``, ``profiles``, ``connections``, ``logs``."""
    return DataLocation(
        settings_file=data_folder / SETTINGS_FILE_NAME,
        profiles_folder=data_folder / PROFILES_FOLDER,
        connections_folder=data_folder / CONNECTIONS_FOLDER,
        log_file=data_folder / "logs" / LOG_FILE_NAME,
        portable=True,
        explicit_folder=data_folder if explicit else None,
    )


def develop_location(application: Path) -> DataLocation:
    """The develop mode: settings, connections and logs in ``DevelopMode``, profiles in starters.

    The profiles written are the ones shipped with the application (``starter_profiles``), not
    those of a user. The connections are not shipped: they stay in ``DevelopMode``.
    """
    folder = application / DEVELOP_FOLDER
    return DataLocation(
        settings_file=folder / SETTINGS_FILE_NAME,
        profiles_folder=application / STARTER_FOLDER,
        connections_folder=folder / CONNECTIONS_FOLDER,
        log_file=folder / "logs" / LOG_FILE_NAME,
        portable=True,
        develop=True,
    )


def known_hosts_file(location: DataLocation) -> Path | None:
    """The file of the host keys ``ssh`` writes, in the portable and develop versions.

    They keep everything in their folder, so ``ssh`` is told to write the keys there and not in
    the ``.ssh`` of the Windows user. ``None`` (local version): the ``known_hosts`` of the system.
    """
    return location.settings_file.parent / "known_hosts" if location.portable else None


def application_folder() -> Path:
    """The folder of the program: beside the executable when packaged, else the repository."""
    if is_packaged():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[4]


def choose_location(
    application: Path, data_folder: Path | None = None, develop: bool = False
) -> DataLocation:
    """``--develop`` first, then ``--data-folder``, then the ``portable`` file, else local."""
    if develop:
        return develop_location(application)
    if data_folder is not None:
        return portable_location(data_folder.resolve(), explicit=True)
    if (application / MARKER_FILE).is_file():
        return portable_location(application / PORTABLE_FOLDER)
    return local_location()
