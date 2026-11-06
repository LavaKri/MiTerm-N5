import sys

import pytest

from n5terminal.core.config.packaged import is_packaged

pytestmark = pytest.mark.unit


def test_a_source_run_is_not_packaged() -> None:
    assert not hasattr(sys, "frozen")
    assert is_packaged() is False


def test_a_packaged_run_is_the_one_where_the_bootloader_sets_frozen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert is_packaged() is True
