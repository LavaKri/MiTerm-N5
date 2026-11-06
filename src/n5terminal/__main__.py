"""Application entry point.

``python -m n5terminal [--folder FOLDER] [--data-folder FOLDER] [--log-level LEVEL] [--develop]
[LAUNCH_FILE]``
"""

import argparse
import logging
from pathlib import Path

import wx

from n5terminal import __version__
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.file_association import FileAssociation, WinRegistry, open_command
from n5terminal.core.config.help import HELP_FOLDER
from n5terminal.core.config.launch_file import LaunchFile, read_launch_file
from n5terminal.core.config.location import (
    DataLocation,
    application_folder,
    choose_location,
    known_hosts_file,
)
from n5terminal.core.config.logging_setup import (
    DEFAULT_LEVEL,
    DEVELOP_LEVEL,
    LOG_LEVELS,
    configure_logging,
    enable_fault_log,
)
from n5terminal.core.config.settings import Settings
from n5terminal.core.config.starter_profiles import offer_starter_profiles
from n5terminal.core.errors import LaunchFileError, ProfileError
from n5terminal.core.session.process_launcher import ProcessLauncher
from n5terminal.i18n import _, install
from n5terminal.ui.beeper import WinsoundBeeper
from n5terminal.ui.main_window import MainWindow
from n5terminal.ui.wx_locale import init_wx_locale

logger = logging.getLogger("n5terminal")


def start_folder(requested: Path | None, settings: Settings) -> Path:
    """The working folder at start: the one asked, else the last one used, else the home folder."""
    candidates = [requested, *(Path(folder) for folder in settings.recent_folders[:1])]
    return next((c for c in candidates if c is not None and c.is_dir()), Path.home())


def open_launch_file(path: Path | None) -> tuple[LaunchFile, list[str]]:
    """What the launch file asks for, and the problems to tell the user.

    Without a file, or with one that cannot be read, nothing is asked: the application starts as if
    none was given.
    """
    if path is None:
        return LaunchFile(), []
    try:
        launch = read_launch_file(path)
    except LaunchFileError as error:
        return LaunchFile(), [str(error)]
    return launch, list(launch.warnings)


def main(argv: list[str] | None = None) -> int:
    """Create the wx application and run the event loop."""
    parser = argparse.ArgumentParser(prog="n5terminal")
    parser.add_argument("--folder", type=Path, help="the working folder of the session")
    parser.add_argument(
        "--data-folder", type=Path, help="keep the settings, profiles and logs in this folder"
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        help=f"what the log file keeps (default: {DEFAULT_LEVEL}, DEBUG with --develop)",
    )
    parser.add_argument(
        "--develop",
        action="store_true",
        help="develop mode: settings and logs in DevelopMode, profiles in starter_profiles",
    )
    parser.add_argument(
        "launch_file",
        nargs="?",
        type=Path,
        help="a launch file (.n5term): profile, variables, folder",
    )
    arguments = parser.parse_args(argv)
    location: DataLocation = choose_location(
        application_folder(), arguments.data_folder, arguments.develop
    )
    log_level = arguments.log_level or (DEVELOP_LEVEL if location.develop else DEFAULT_LEVEL)
    configure_logging(location.log_file, log_level)
    if location.develop:
        enable_fault_log(location.log_file)
    logger.info(
        "MiTerm-N5 %s starts (%s data, log level %s)",
        __version__,
        "develop" if location.develop else "portable" if location.portable else "local",
        log_level,
    )
    settings = Settings.load(location.settings_file)
    install(settings.language)
    app = wx.App()
    locale = init_wx_locale(settings.language)  # must stay referenced while the app runs
    starter_problems: list[str] = []
    if not location.develop:  # in develop mode the starter profiles are the profiles
        try:
            offer_starter_profiles(application_folder(), location.profiles_folder)
        except ProfileError as error:
            starter_problems.append(str(error))
    launch, launch_problems = open_launch_file(arguments.launch_file)
    folder = start_folder(arguments.folder or launch.folder, settings)
    # Portable mode must leave nothing on the computer: no association then.
    association = None if location.portable else FileAssociation(WinRegistry(), open_command())
    window = MainWindow(
        settings,
        ProcessLauncher(known_hosts_file(location)),
        folder,
        AppContext.from_location(location, association, application_folder() / HELP_FOLDER),
        WinsoundBeeper(),
    )
    window.Maximize(settings.maximize_at_start)
    window.Show()
    launch_problems += window.actions.apply_launch_file(launch)
    startup_problems = (  # a launch file that names a profile is the start
        window.actions.apply_startup_profile(settings.startup_profile)
        if launch.profile is None
        else []
    )
    if startup_problems:
        window.feedback.show_error(
            _("The startup profile could not be applied.\n{details}").format(
                details="\n".join(startup_problems)
            )
        )
    if launch_problems:
        window.feedback.show_error(
            _("The launch file could not be applied completely.\n{details}").format(
                details="\n".join(launch_problems)
            )
        )
    if window.connection_warnings:
        window.feedback.show_error(
            _("A connection file could not be read or used.\n{details}").format(
                details="\n".join(window.connection_warnings)
            )
        )
    profile_problems = [*starter_problems, *window.profile_warnings]
    if profile_problems:
        window.feedback.show_error(
            _("A profile file could not be read.\n{details}").format(
                details="\n".join(profile_problems)
            )
        )
    if settings.load_warning:
        window.feedback.show_error(
            _("A configuration file could not be read.\n{details}").format(
                details=settings.load_warning
            )
        )
    app.MainLoop()
    del locale
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
