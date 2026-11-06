"""The logic of the catalogs dialog of the develop mode (see "Catalogs" in ``specs/interface.md``).

One list, one column. A line shows either the id of a message or its translation in a language;
Left and Right change what the lines show, Up and Down move as usual. The field below holds the text
of the selected line: the id (read only) or the translation (changes go to the catalog).
The ids are never changed.
"""

from n5terminal.core.config.catalogs import Catalogs, fields_of
from n5terminal.i18n import N_, _

EXCERPT_LENGTH = 50  # a line of the list stops at the first line break or after this many
ALL = "all"
UNTRANSLATED = "untranslated"
LANGUAGE_NAMES = {"fr": N_("French"), "en": N_("English")}

# The category of a message comes from the source files that use it; the first matching part wins.
CATEGORY_FILES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("menus", ("ui/main_menu.py", "ui/menus.py")),
    (
        "preferences",
        ("_page.py", "ui/preferences_dialog.py", "_preferences.py", "core/config/shortcuts.py"),
    ),
    (
        "announcements",
        (
            "core/config/announcements.py",
            "core/config/screen_reader.py",
            "presenters/session_presenter.py",
        ),
    ),
    (
        "dialogs",
        (
            "_dialog.py",
            "ui/feedback.py",
            "ui/output_commands.py",
            "ui/actions.py",
            "presenters/profile_editor.py",
        ),
    ),
)
OTHER = "other"


def _excerpt(text: str) -> str:
    """The first line of ``text``, cut at ``EXCERPT_LENGTH``; marked as an excerpt when cut."""
    first = text.split("\n", 1)[0]
    if len(first) <= EXCERPT_LENGTH and first == text:
        return text
    return _("{text}... Message excerpt").format(text=first[:EXCERPT_LENGTH])


def category_labels() -> dict[str, str]:
    return {
        ALL: _("All"),
        UNTRANSLATED: _("Not translated"),
        "menus": _("Menus"),
        "preferences": _("Preferences"),
        "announcements": _("Announcements"),
        "dialogs": _("Dialogs"),
        OTHER: _("Other"),
    }


def categories_of(files: tuple[str, ...]) -> set[str]:
    """The categories of a message used in ``files`` (``other`` if none matches)."""
    found = {
        category
        for category, parts in CATEGORY_FILES
        for name in files
        if any(part in name for part in parts)
    }
    return found or {OTHER}


class CatalogsEditor:
    """The state of the dialog: the category, the view (ids or a language), the selected line."""

    def __init__(self, catalogs: Catalogs) -> None:
        self._catalogs = catalogs
        self._labels = category_labels()
        self.category_ids = [ALL, UNTRANSLATED, "menus", "preferences", "announcements"]
        self.category_ids += ["dialogs", OTHER]
        self.category_index = 0
        self._view = 0  # 0: the ids, then one per language
        self._shown: list[str] = []  # the ids of the lines
        self.selected = 0
        self.choose_category(0)

    @property
    def category_names(self) -> list[str]:
        return [self._labels[category] for category in self.category_ids]

    def choose_category(self, index: int) -> None:
        """Show the messages of a category, from the first line.

        The list is made now and not again while the translations change, so that a message does
        not leave the list under the cursor when it becomes translated.
        """
        self.category_index = index
        category = self.category_ids[index]
        self._shown = [
            message_id
            for message_id in self._catalogs.ids
            if self._in_category(message_id, category)
        ]
        self.selected = 0

    def _in_category(self, message_id: str, category: str) -> bool:
        if category == ALL:
            return True
        if category == UNTRANSLATED:
            return any(
                not self._catalogs.text(language, message_id)
                for language in self._catalogs.languages
            )
        return category in categories_of(self._catalogs.files.get(message_id, ()))

    @property
    def language(self) -> str | None:
        """The language the lines show; ``None`` when they show the ids."""
        return self._catalogs.languages[self._view - 1] if self._view else None

    def change_view(self, step: int) -> bool:
        """Show the next (+1) or previous (-1) kind of line; whether it changed."""
        view = self._view + step
        if not 0 <= view <= len(self._catalogs.languages):
            return False
        self._view = view
        return True

    def lines(self) -> list[str]:
        """The lines of the list, in the current view."""
        return [self._line(message_id) for message_id in self._shown]

    def _line(self, message_id: str) -> str:
        language = self.language
        if language is None:
            return _excerpt(message_id)
        text = self._catalogs.text(language, message_id)
        return _excerpt(text) if text else _("(not translated)")

    def select(self, index: int) -> None:
        if 0 <= index < len(self._shown):
            self.selected = index

    @property
    def message_id(self) -> str | None:
        return self._shown[self.selected] if self._shown else None

    @property
    def field_label(self) -> str:
        language = self.language
        if language is None:
            return _("Message")
        name = _(LANGUAGE_NAMES[language]) if language in LANGUAGE_NAMES else language
        return _("Message in {language}").format(language=name)

    @property
    def read_only(self) -> bool:
        """The ids cannot be changed."""
        return self.language is None

    @property
    def field_text(self) -> str:
        message_id = self.message_id
        if message_id is None:
            return ""
        language = self.language
        return message_id if language is None else self._catalogs.text(language, message_id)

    def edit(self, text: str) -> None:
        """Put ``text`` in the catalog for the selected message (ignored when the ids are shown)."""
        message_id, language = self.message_id, self.language
        if message_id is None or language is None:
            return
        if "\n" not in message_id:
            text = text.replace("\r\n", " ").replace("\n", " ")  # a one line message stays so
        self._catalogs.set_text(language, message_id, text)

    def check(self) -> str | None:
        """What is wrong with the changes, or ``None``; the faulty message is then selected.

        A translation must have the same ``{fields}`` as its id, or the program would fail when it
        shows the message.
        """
        found = self._catalogs.problem()
        if found is None:
            return None
        language, message_id = found
        self._show_in_view(message_id, self._catalogs.languages.index(language) + 1)
        names = ", ".join("{" + name + "}" for name in sorted(fields_of(message_id) or ()))
        return _("The fields of the message must be the same as in its id: {fields}.").format(
            fields=names or _("none")
        )

    def _show_in_view(self, message_id: str, view: int) -> None:
        self._view = view
        self.choose_category(0)
        self.selected = self._shown.index(message_id)

    def save(self) -> None:
        """Write the catalogs (``CatalogError`` if a file cannot be written)."""
        self._catalogs.save()
