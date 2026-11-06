from pathlib import Path

import pytest

from fakes.session_support import Session, run_program
from n5terminal import __version__
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.location import develop_location, local_location, portable_location
from n5terminal.presenters.session_report import data_mode, session_report

pytestmark = pytest.mark.unit


def report(session: Session, context: AppContext | None = None, lines: int = 3) -> list[str]:
    text = session_report(
        session.presenter,
        session.settings,
        context or AppContext(),
        output_lines=lines,
        terminal_view_only=False,
    )
    return text.splitlines()


def test_the_data_mode_is_normal_without_a_location(tmp_path: Path) -> None:
    assert data_mode(AppContext()) == "normal"
    assert data_mode(AppContext(location=local_location())) == "normal"
    assert data_mode(AppContext(location=portable_location(tmp_path))) == "portable"
    assert data_mode(AppContext(location=develop_location(tmp_path))) == "develop"


def test_the_report_tells_the_folder_the_program_and_the_version(session: Session) -> None:
    lines = report(session)
    assert f"Working folder: {session.folder}" in lines
    assert "Running program: none" in lines
    assert "Launch mode: CLI" in lines
    assert f"Version: {__version__}" in lines
    run_program(session, "ping host")
    assert "Running program: ping" in report(session)


def test_the_report_counts_the_lines_of_the_output_against_the_limit(session: Session) -> None:
    limit = session.settings.output_limit
    assert f"Output lines: 7 of {limit}" in report(session, lines=7)


def test_the_files_are_those_of_the_location(session: Session, tmp_path: Path) -> None:
    location = portable_location(tmp_path)
    lines = report(session, AppContext(location=location))
    assert f"Settings file: {location.settings_file}" in lines
    assert f"Profiles folder: {location.profiles_folder}" in lines
    assert f"Log file: {location.log_file}" in lines
    assert "Settings file: none" in report(session)
