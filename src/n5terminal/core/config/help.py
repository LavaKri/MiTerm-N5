"""The help: one page per language in the ``Help`` folder, written in Markdown and read as HTML.

``Fr.md`` and ``En.md`` are the sources; ``Fr.html`` and ``En.html`` are made from them by the
Develop menu (``convert_help``) and opened in the default browser by Help > Open the help. See
"Help" in ``specs/interface.md``.
"""

import html
from itertools import pairwise
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from n5terminal.core.errors import HelpError

HELP_FOLDER = "Help"
FALLBACK_LANGUAGE = "en"


def help_name(language: str) -> str:
    """The name a page of ``language`` has, without extension: ``fr`` is ``Fr``."""
    return language.capitalize()


def help_page(folder: Path, language: str) -> Path | None:
    """The HTML page of ``language``, else the English one, None when there is neither."""
    for candidate in (language, FALLBACK_LANGUAGE):
        page = folder / f"{help_name(candidate)}.html"
        if page.is_file():
            return page
    return None


def to_html(markdown: str, language: str, name: str) -> str:
    """The simplest page for ``markdown``: no style, no script, only what a browser needs.

    The browser needs the character set to show the accents, a language for the screen reader, and
    a title, which a screen reader reads when the page opens: the first heading, else ``name``.
    """
    parser = MarkdownIt()
    title = _first_heading(parser.parse(markdown)) or name
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{html.escape(language, quote=True)}">\n'
        '<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        "</head>\n<body>\n"
        f"{parser.render(markdown)}"
        "</body>\n</html>\n"
    )


def _first_heading(tokens: list[Token]) -> str:
    """The text of the first heading, empty when there is none."""
    for before, token in pairwise(tokens):
        if before.type == "heading_open" and token.type == "inline":
            return token.content
    return ""


def convert_help(folder: Path) -> list[Path]:
    """Write ``xx.html`` beside each ``xx.md`` of ``folder``; the pages written.

    Raises :class:`HelpError` when the folder or a file cannot be read or written.
    """
    try:
        sources = sorted(folder.glob("*.md"))
    except OSError as error:
        raise HelpError(str(error)) from error
    if not sources:
        raise HelpError(f"{folder}: no .md file")
    written: list[Path] = []
    for source in sources:
        target = source.with_suffix(".html")
        try:
            markdown = source.read_text(encoding="utf-8")
            page = to_html(markdown, source.stem.lower(), source.stem)
            target.write_text(page, encoding="utf-8", newline="\n")
        except OSError as error:
            raise HelpError(f"{source.name}: {error}") from error
        written.append(target)
    return written
