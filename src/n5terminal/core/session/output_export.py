"""Writing the output to a text file the user chose (see "Export" in ``specs/robustness.md``)."""

from pathlib import Path

from n5terminal.core.errors import ExportError


def export_output(path: Path, text: str) -> None:
    """Write ``text`` (``\\n`` as line break) to ``path`` as UTF-8, with Windows line breaks.

    The last line ends with a line break, as a text file does. Raises :class:`ExportError`.
    """
    if text and not text.endswith("\n"):
        text += "\n"
    try:
        path.write_text(text, encoding="utf-8", newline="\r\n")
    except OSError as error:
        raise ExportError(str(error)) from error
