"""The message catalogs the develop mode edits (see "Catalogs" in ``specs/interface.md``).

A catalog is a ``.po`` file per language; the template (``n5terminal.pot``) holds the message ids
and the source file of each. The ids are never changed here, only the translations. Babel reads
and writes the files; it is a development tool, and this module is only used in the develop mode.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
from typing import BinaryIO

from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

from n5terminal.core.errors import CatalogError

TEMPLATE_NAME = "n5terminal.pot"
CATALOG_PATH = "{language}/LC_MESSAGES/n5terminal.po"


def fields_of(text: str) -> set[str] | None:
    """The named fields (``{details}``) of ``text``; ``None`` if its braces are not valid."""
    try:
        return {name for _literal, name, _spec, _conv in Formatter().parse(text) if name}
    except ValueError:
        return None


def _file_name(location: str) -> str:
    return location.replace("\\", "/")


@dataclass(slots=True)
class Catalogs:
    """The template and the catalogs of a locale folder, with the translations changed."""

    folder: Path
    ids: list[str]
    files: dict[str, tuple[str, ...]]  # message id -> source files, from the template
    catalogs: dict[str, Catalog]  # language -> catalog
    changed: set[tuple[str, str]] = field(default_factory=set)  # (language, message id)

    @property
    def languages(self) -> list[str]:
        return sorted(self.catalogs)

    @classmethod
    def load(cls, folder: Path) -> Catalogs:
        """Read the template and every catalog under ``folder``; ``CatalogError`` if one fails."""
        ids: list[str] = []
        files: dict[str, tuple[str, ...]] = {}
        template = folder / TEMPLATE_NAME
        if template.is_file():
            for message in _read(template):
                if message.id:
                    ids.append(str(message.id))
                    files[str(message.id)] = tuple(
                        sorted({_file_name(name) for name, _line in message.locations})
                    )
        catalogs: dict[str, Catalog] = {}
        for path in sorted(folder.glob(CATALOG_PATH.format(language="*"))):
            catalogs[path.parent.parent.name] = _read(path, path.parent.parent.name)
        known = set(ids)
        for catalog in catalogs.values():
            for message in catalog:
                if message.id and str(message.id) not in known:
                    ids.append(str(message.id))
                    known.add(str(message.id))
        return cls(folder, ids, files, catalogs)

    def text(self, language: str, message_id: str) -> str:
        """The translation of ``message_id``; empty if it has none."""
        message = self.catalogs[language].get(message_id)
        return str(message.string) if message is not None and message.string else ""

    def set_text(self, language: str, message_id: str, text: str) -> None:
        """Change a translation; the message must exist in the catalog."""
        message = self.catalogs[language].get(message_id)
        if message is None:
            raise CatalogError(f"The message {message_id!r} is not in the catalog {language}.")
        if message.string != text:
            message.string = text
            self.changed.add((language, message_id))

    def problem(self) -> tuple[str, str] | None:
        """The first changed translation whose fields differ from the id's: (language, id)."""
        for language, message_id in sorted(self.changed):
            if fields_of(self.text(language, message_id)) != fields_of(message_id):
                return language, message_id
        return None

    def save(self) -> None:
        """Write the ``.po`` and ``.mo`` of each changed catalog; ``CatalogError`` if one fails.

        Each file is written whole beside the old one, then replaces it.
        """
        for language in sorted({language for language, _id in self.changed}):
            path = self.folder / CATALOG_PATH.format(language=language)
            catalog = self.catalogs[language]
            write_catalog_po(path, catalog)
            _write_mo(path.with_suffix(".mo"), catalog)
        self.changed.clear()


def _read(path: Path, locale: str | None = None) -> Catalog:
    try:
        with path.open("rb") as file:
            return read_po(file, locale=locale)
    except (OSError, ValueError) as error:
        raise CatalogError(f"Cannot read {path}: {error}") from error


def write_catalog_po(path: Path, catalog: Catalog) -> None:
    """Write ``catalog`` as a ``.po`` file."""
    _write(path, lambda file: write_po(file, catalog))


def _write_mo(path: Path, catalog: Catalog) -> None:
    _write(path, lambda file: write_mo(file, catalog))


def _write(path: Path, write: Callable[[BinaryIO], None]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("wb") as file:
            write(file)
        temporary.replace(path)
    except OSError as error:
        raise CatalogError(f"Cannot write {path}: {error}") from error
