"""Starter profiles: the profiles shipped in the application folder, offered once to the user.

See "Starter profiles" in ``specs/interface.md``. Each file of the starter profiles folder of the
application (``starter_profiles`` at the root of the repository, ``_internal/StartProfil`` in the
packaged application) is copied to the profiles folder of the user the first time it is seen,
unless the user already has a profile of that name. The names already offered are written in a
marker file of the profiles folder, so that a profile the user deleted or changed never comes back
or is overwritten.
"""

import shutil
from pathlib import Path

from n5terminal.core.config.packaged import is_packaged
from n5terminal.core.config.profiles import PROFILE_SUFFIX
from n5terminal.core.errors import ProfileError

STARTER_FOLDER = "starter_profiles"  # at the root of the repository
PACKAGED_FOLDER = "StartProfil"  # in the ``_internal`` folder of the packaged application
INTERNAL_FOLDER = "_internal"
OFFERED_FILE = ".starters"  # not a ``.json`` file: it is never read as a profile


def _offered(target: Path) -> set[str]:
    try:
        text = (target / OFFERED_FILE).read_text(encoding="utf-8")
    except FileNotFoundError:
        return set()
    except OSError as error:
        raise ProfileError(f"Cannot read {target / OFFERED_FILE}: {error}") from error
    return {line.strip().casefold() for line in text.splitlines() if line.strip()}


def starter_folder(application: Path, packaged: bool | None = None) -> Path:
    """The folder of the starter profiles; ``packaged`` is whether the application is (default:
    ``is_packaged()``)."""
    if is_packaged() if packaged is None else packaged:
        return application / INTERNAL_FOLDER / PACKAGED_FOLDER
    return application / STARTER_FOLDER


def offer_starter_profiles(
    application: Path, target: Path, packaged: bool | None = None
) -> list[str]:
    """Copy the starter profiles not offered yet into ``target``; the names copied.

    Without starter folder nothing happens. Raises ``ProfileError`` if a file cannot be read or
    written.
    """
    source = starter_folder(application, packaged)
    if not source.is_dir():
        return []
    offered = _offered(target)
    known = set(offered)
    copied: list[str] = []
    try:
        target.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.glob(f"*{PROFILE_SUFFIX}")):
            if path.stem.casefold() in offered:
                continue
            destination = target / path.name
            if not destination.exists():
                shutil.copyfile(path, destination)
                copied.append(path.stem)
            offered.add(path.stem.casefold())
        if offered != known:
            (target / OFFERED_FILE).write_text("\n".join(sorted(offered)) + "\n", encoding="utf-8")
    except OSError as error:
        raise ProfileError(f"Cannot offer the starter profiles in {target}: {error}") from error
    return copied
