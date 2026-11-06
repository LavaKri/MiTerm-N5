from pathlib import Path

import pytest

from n5terminal.core.errors import ExportError
from n5terminal.core.session.output_export import export_output

pytestmark = pytest.mark.unit


def test_the_text_is_written_as_utf8_with_windows_line_breaks(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    export_output(target, "# dir\nété\n")
    assert target.read_bytes() == "# dir\r\nété\r\n".encode()


def test_the_last_line_ends_with_a_line_break(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    export_output(target, "a\nb")
    assert target.read_bytes() == b"a\r\nb\r\n"


def test_an_existing_file_is_replaced(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old text that is longer", encoding="utf-8")
    export_output(target, "new\n")
    assert target.read_bytes() == b"new\r\n"


def test_a_file_that_cannot_be_written_is_an_export_error(tmp_path: Path) -> None:
    with pytest.raises(ExportError):
        export_output(tmp_path / "missing" / "out.txt", "a\n")
