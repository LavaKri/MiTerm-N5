"""The launch file: a small ``.ini`` that tells a new session its profile, variables and folder.

See "Launch file" in ``specs/interface.md``. One ``key = value`` per line, no section needed. The
keys are the names of the variables (``name``, ``source``, ``destination``, ``value1``, ``value2``,
with or without braces), ``profile`` and ``WorkingPath``; the case is ignored, an unknown key too.
The file runs nothing: it only chooses.
"""

import configparser
from dataclasses import dataclass, field
from pathlib import Path

from n5terminal.core.config.profiles import VARIABLES
from n5terminal.core.errors import LaunchFileError
from n5terminal.i18n import _

LAUNCH_FILE_EXTENSION = ".n5term"
PROFILE_KEY = "profile"
WORKING_PATH_KEY = "workingpath"
_SECTION = "launch"


@dataclass(slots=True)
class LaunchFile:
    """What the file asks for. ``folder`` is the working folder to start in (None: the usual one).

    ``warnings`` say, in the language of the application, what was not applied; the window shows
    them to the user.
    """

    profile: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
    folder: Path | None = None
    warnings: list[str] = field(default_factory=list)


def _normalize_key(key: str) -> str:
    """The key without braces, in lower case; ``email`` of older files is ``comment``."""
    name = key.strip().strip("{}").strip().casefold()
    return "comment" if name == "email" else name


def _parse(path: Path) -> dict[str, str]:
    """The keys (normalized) and values of the file; raises ``LaunchFileError``."""
    parser = configparser.ConfigParser(
        delimiters=("=",),
        comment_prefixes=(";", "#"),
        inline_comment_prefixes=None,
        interpolation=None,
        strict=False,
    )
    parser.optionxform = _normalize_key  # type: ignore[assignment,method-assign]
    try:
        text = path.read_text(encoding="utf-8-sig")
        parser.read_string(f"[{_SECTION}]\n{text}")  # the file has no section of its own
    except (OSError, UnicodeDecodeError, configparser.Error) as error:
        raise LaunchFileError(
            _("Cannot read {file}: {error}").format(file=path, error=error)
        ) from error
    return {
        key: value.strip() for section in parser.sections() for key, value in parser.items(section)
    }


def read_launch_file(path: Path) -> LaunchFile:
    """Read the launch file ``path``. Raises ``LaunchFileError`` if it cannot be read."""
    values = _parse(path)
    launch = LaunchFile()
    launch.profile = values.get(PROFILE_KEY) or None
    launch.variables = {name: values[name] for name in VARIABLES if values.get(name)}
    if launch.variables and launch.profile is None:
        launch.warnings.append(
            _("{file}: the variables are ignored because the file has no profile.").format(
                file=path.name
            )
        )
        launch.variables = {}
    own_folder = path.resolve().parent
    asked = values.get(WORKING_PATH_KEY)
    if not asked:
        launch.folder = own_folder
        return launch
    folder = Path(asked)
    folder = folder if folder.is_absolute() else own_folder / folder
    if folder.is_dir():
        launch.folder = folder
    else:
        launch.warnings.append(
            _("{file}: the working folder {folder} does not exist.").format(
                file=path.name, folder=folder
            )
        )
    return launch
