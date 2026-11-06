"""The text of the session information dialog, gathered from the session and the data location.

The window gives what only it knows (the lines of the output area and the terminal view); the rest
comes from the presenter, the settings and the location. Nothing here knows about ``wx``.
"""

from n5terminal import __version__
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.settings import Settings
from n5terminal.i18n import N_, _
from n5terminal.presenters.session_info import SessionInfo, session_info_lines
from n5terminal.presenters.session_presenter import SessionPresenter


def data_mode(context: AppContext) -> str:
    """How the data is kept, as a message id: normal, portable or develop."""
    location = context.location
    if location is None or not location.portable:
        return N_("normal")
    return N_("develop") if location.develop else N_("portable")


def session_report(
    presenter: SessionPresenter,
    settings: Settings,
    context: AppContext,
    *,
    output_lines: int,
    terminal_view_only: bool,
) -> str:
    """One line per information about the session, ``Name: value``."""
    state = presenter.state
    size = presenter.terminal_size
    location = context.location
    info = SessionInfo(
        folder=presenter.working_folder,
        profile=state.profile,
        program=presenter.running_program,
        last_end=presenter.last_end_text,
        launch_mode=state.effective_launch_mode.value.upper(),
        interpreter=state.interpreter,
        terminal_size=f"{size.columns} x {size.rows}",
        terminal_view_only=terminal_view_only,
        output_lines=output_lines,
        output_limit=settings.output_limit,
        data_mode=data_mode(context),
        settings_file=location.settings_file if location else None,
        profiles_folder=location.profiles_folder if location else None,
        log_file=location.log_file if location else None,
        version=__version__,
        connection=state.connection,
        connection_target=presenter.connection_target,
        connection_state=presenter.connection_state,
        connected_for=presenter.connected_for,
        ssh_path=settings.ssh_path,
        connections_folder=location.connections_folder if location else None,
    )
    return "\n".join(session_info_lines(info, _))
