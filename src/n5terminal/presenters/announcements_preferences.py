"""The Announcements page of the Preferences: the output, and where each category goes.

See "Preferences" in ``specs/interface.md``. The categories are listed in the alphabetical order
of their names (accents and case ignored), each line saying the category then its destination, so
that nothing depends on columns.
"""

import sys
import unicodedata
from collections.abc import Callable

from n5terminal.core.config.announcements import CATEGORIES, Category, Destination
from n5terminal.core.config.screen_reader import Output, available_outputs
from n5terminal.core.config.settings import ACTIVITY_INTERVALS, Settings
from n5terminal.i18n import N_
from n5terminal.presenters.preferences_changes import AppliedChanges

Translate = Callable[[str], str]
LINE_FORMAT = N_("{category}, {destination}")  # the category, then its destination


def _sort_key(text: str) -> str:
    """The text without accents and case, to put names in alphabetical order."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


class AnnouncementsPreferences:
    """The draft of the destinations, started from ``settings``; ``translate`` is ``_``."""

    def __init__(
        self, settings: Settings, translate: Translate, platform: str = sys.platform
    ) -> None:
        self._settings = settings
        self._translate = translate
        self._platform = platform
        self.screen_reader_output = settings.screen_reader_output
        self.activity_interval = settings.activity_interval
        self.activity_only_in_output = settings.activity_only_in_output
        self._destinations = {c.id: settings.destination_for(c) for c in CATEGORIES}
        self._categories = sorted(CATEGORIES, key=lambda c: _sort_key(translate(c.label)))

    def output_choices(self) -> list[Output]:
        """The ways to send the announcements to the screen reader that work on this system."""
        return list(available_outputs(self._platform))

    def output_name(self, output: Output) -> str:
        return self._translate(output.label)

    def select_output(self, output_id: str) -> None:
        """Choose an output; one that does not exist here is ignored."""
        if any(output.id == output_id for output in self.output_choices()):
            self.screen_reader_output = output_id

    def set_activity_interval(self, seconds: int) -> None:
        """Choose the seconds between two checks of the activity; one out of range is ignored."""
        if seconds in ACTIVITY_INTERVALS:
            self.activity_interval = seconds

    def categories(self) -> list[Category]:
        """Every category, in the alphabetical order of its name."""
        return list(self._categories)

    def category_name(self, category: Category) -> str:
        return self._translate(category.label)

    def destination_name(self, destination: Destination) -> str:
        return self._translate(destination.label)

    def choices(self, category: Category) -> list[Destination]:
        """The destinations ``category`` accepts."""
        return list(category.choices)

    def destination(self, category: Category) -> Destination:
        return self._destinations[category.id]

    def select(self, category: Category, destination: Destination) -> None:
        """Send the announcements of ``category`` to ``destination`` (if it accepts it)."""
        if category.accepts(destination):
            self._destinations[category.id] = destination

    def line(self, category: Category) -> str:
        """The category then its destination, in one text."""
        return self._translate(LINE_FORMAT).format(
            category=self.category_name(category),
            destination=self.destination_name(self.destination(category)),
        )

    def apply(self) -> AppliedChanges:
        """Write the draft to the settings (not to the file) and tell if something changed."""
        changed = False
        for category in CATEGORIES:
            chosen = self._destinations[category.id]
            if chosen is not self._settings.destination_for(category):
                self._settings.set_destination(category, chosen)
                changed = True
        if (
            self.activity_interval != self._settings.activity_interval
            or self.activity_only_in_output != self._settings.activity_only_in_output
        ):
            self._settings.activity_interval = self.activity_interval
            self._settings.activity_only_in_output = self.activity_only_in_output
            changed = True
        output_changed = self.screen_reader_output != self._settings.screen_reader_output
        self._settings.screen_reader_output = self.screen_reader_output
        return AppliedChanges(announcements=changed, screen_reader_output=output_changed)
