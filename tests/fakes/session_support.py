"""What the tests of the session presenter share: a session with its fakes, and small scenarios."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fakes.fake_launcher import FakeLauncher
from fakes.fake_transport import FakeTransport
from fakes.fake_view import FakeView
from fakes.recording_sinks import RecordingBeeper, RecordingMessageSink
from n5terminal.core.config.announcements import AnnouncementCenter, Category, Destination
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import Interpreter, Mode
from n5terminal.presenters.session_presenter import SessionPresenter
from n5terminal.presenters.session_run import SessionServices


@dataclass
class Session:
    presenter: SessionPresenter
    view: FakeView
    launcher: FakeLauncher
    sink: RecordingMessageSink
    settings: Settings
    folder: Path
    now: list[float]
    beeper: RecordingBeeper

    @property
    def transport(self) -> FakeTransport:
        return self.launcher.transport


def make_session(
    tmp_path: Path,
    mode: Mode | None = None,
    destination_of: Callable[[Category], Destination] | None = None,
) -> Session:
    view, launcher, sink = FakeView(), FakeLauncher(mode), RecordingMessageSink()
    settings, now, beeper = Settings.load(None), [0.0], RecordingBeeper()
    services = SessionServices(
        launcher,
        settings,
        AnnouncementCenter(sink, destination_of, beeper=beeper),
        post=lambda action: action(),
        clock=lambda: now[0],
    )
    presenter = SessionPresenter(view, services, tmp_path)
    return Session(presenter, view, launcher, sink, settings, tmp_path, now, beeper)


def run_program(session: Session, line: str = "ping host") -> None:
    session.presenter.submit(line)
    session.presenter.tick()


def end_program(session: Session, code: int = 0) -> None:
    session.transport.exit(code)
    session.presenter.tick()


def show_prompt(session: Session, text: bytes = b"C:\\work>") -> None:
    """The shell shows ``text`` (by default its prompt) and the UI takes it."""
    session.transport.receive(text)
    session.presenter.tick()


def start_shell(session: Session, line: str = "dir") -> None:
    assert session.presenter.set_interpreter(Interpreter.CMD)
    session.presenter.submit(line)
