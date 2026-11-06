from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from fakes.session_support import Session, make_session
from n5terminal.core.session.session_state import Mode

if TYPE_CHECKING:
    import wx

# The contract tests live in a shared module, not in a test file: show their assertion details.
pytest.register_assert_rewrite("fakes.screen_model_contract")


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """A session of the presenter whose programs run with pipes."""
    return make_session(tmp_path)


@pytest.fixture
def terminal(tmp_path: Path) -> Session:
    """A session of the presenter whose programs run under a terminal."""
    return make_session(tmp_path, Mode.TERMINAL_LINE)


@pytest.fixture(scope="session")
def app() -> wx.App:
    """The one wx application of the ui tests (wx is only loaded when a test asks for it)."""
    import wx as wx_module  # noqa: PLC0415

    return wx_module.App()
