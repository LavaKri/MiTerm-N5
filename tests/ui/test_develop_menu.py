"""The test programs listed by the Develop menu."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import wx

from fakes.fake_launcher import FakeLauncher
from n5terminal.core.config.app_context import AppContext
from n5terminal.core.config.settings import Settings
from n5terminal.core.session.session_state import CommandId
from n5terminal.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


@pytest.fixture
def window(app: wx.App, tmp_path: Path) -> Iterator[MainWindow]:
    folder = tmp_path / "DevelopMode"
    (folder / "testprograms").mkdir(parents=True)
    for name in ("Beta.py", "Alpha.py", "_common.py", "notes.txt"):
        (folder / "testprograms" / name).write_text("", encoding="utf-8")
    frame = MainWindow(
        Settings.load(None), FakeLauncher(), tmp_path, AppContext(develop_folder=folder)
    )
    yield frame
    frame.Close(force=True)


def test_the_menu_lists_the_programs_and_not_the_helpers(window: MainWindow) -> None:
    assert [path.name for path in window.actions.test_programs()] == ["Alpha.py", "Beta.py"]


def test_the_session_information_tells_the_type_of_session_and_the_folder(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        window.feedback, "show_text", lambda title, text: shown.append((title, text))
    )
    window.actions.run(CommandId.SESSION_INFO)
    assert len(shown) == 1
    title, text = shown[0]
    assert title == "Session information"
    assert f"Working folder: {window.presenter.working_folder}" in text.splitlines()
    assert "Session type: normal" in text.splitlines()  # no location given to the test window


def test_the_title_of_the_window_names_the_profile_and_the_folder(window: MainWindow) -> None:
    folder = window.presenter.working_folder
    assert window.GetTitle() == f"MiTerm-N5: free profile in {folder.name}"
