import pytest

from fakes.screen_model_contract import ScreenModelContract
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.screen_model import ScreenModel

pytestmark = pytest.mark.unit


class TestPyteScreenModel(ScreenModelContract):
    def make_model(self, columns: int = 80, rows: int = 24) -> ScreenModel:
        return PyteScreenModel(columns, rows)
