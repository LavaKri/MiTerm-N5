import pytest

from n5terminal.core.config.announcements import (
    ACTIVITY,
    CATEGORIES,
    FOLDER,
    MOVEMENT,
    PROGRAM,
    SEARCH_FAILED,
    Destination,
)
from n5terminal.core.config.screen_reader import NONE, UIA
from n5terminal.core.config.settings import Settings
from n5terminal.presenters.announcements_preferences import AnnouncementsPreferences
from n5terminal.presenters.preferences_changes import AppliedChanges

pytestmark = pytest.mark.unit

FRENCH = {
    "State of the program": "État du programme",
    "Session, settings": "Session, réglages",
    "Session, change": "Session, changement",
    "Output, movement and reading": "Sortie, déplacement et lecture",
    "Output, no more elements": "Sortie, pas ou plus d'éléments",
    "Output, read the line": "Sortie, lire la ligne",
    "Output, keys sent": "Sortie, touches envoyées",
    "Command not possible": "Commande impossible",
    "Launch failure": "Échec de lancement",
    "Search reached": "Recherche atteinte",
    "Unsuccessful search": "Recherche sans résultat",
    "No announcement": "Aucune annonce",
    "Message": "Message",
    "Read the line": "Lire la ligne",
    "Dialog box": "Boîte de dialogue",
    "{category}, {destination}": "{category}, {destination}",
}


def translate(text: str) -> str:
    return FRENCH.get(text, text)


def page(settings: Settings | None = None) -> AnnouncementsPreferences:
    return AnnouncementsPreferences(settings or Settings(), translate)


def test_the_categories_are_in_the_alphabetical_order_of_their_names_without_accents() -> None:
    names = [page().category_name(category) for category in page().categories()]
    assert names[0] == "Commande impossible"
    assert names.index("Échec de lancement") < names.index("État du programme")  # no accents
    assert names.index("Session, changement") + 1 == names.index("Session, réglages")
    outputs = [i for i, name in enumerate(names) if name.startswith("Sortie, ")]
    assert len(outputs) == 4
    assert outputs == list(range(outputs[0], outputs[0] + 4))
    assert len(names) == len(CATEGORIES)


def test_each_destination_starts_from_the_settings() -> None:
    settings = Settings()
    settings.set_destination(FOLDER, Destination.NONE)
    preferences = page(settings)
    assert preferences.destination(FOLDER) is Destination.NONE
    assert preferences.destination(PROGRAM) is PROGRAM.default


def test_a_line_says_the_category_then_its_destination() -> None:
    assert page().line(FOLDER) == "Session, réglages, Message"


def test_only_the_destinations_a_category_accepts_can_be_chosen() -> None:
    preferences = page()
    preferences.select(FOLDER, Destination.READ_LINE)  # a folder cannot read a line
    assert preferences.destination(FOLDER) is FOLDER.default
    preferences.select(MOVEMENT, Destination.READ_LINE)
    assert preferences.destination(MOVEMENT) is Destination.READ_LINE
    assert Destination.DIALOG in preferences.choices(SEARCH_FAILED)


def test_nothing_changed_says_so() -> None:
    assert page().apply() == AppliedChanges()


def test_apply_writes_only_what_differs_from_the_default() -> None:
    settings = Settings()
    preferences = page(settings)
    preferences.select(FOLDER, Destination.NONE)
    assert preferences.apply() == AppliedChanges(announcements=True)
    assert settings.announcements == {"folder": "none"}
    preferences.select(FOLDER, FOLDER.default)
    assert preferences.apply().announcements
    assert settings.announcements == {}


def test_changes_of_both_pages_are_merged() -> None:
    merged = AppliedChanges(language=True).merged(AppliedChanges(announcements=True))
    assert (merged.language, merged.announcements, merged.output_limit) == (True, True, False)


def test_the_output_starts_from_the_settings_and_ui_automation_is_offered_on_windows() -> None:
    settings = Settings(screen_reader_output=NONE.id)
    windows = AnnouncementsPreferences(settings, translate, "win32")
    assert windows.screen_reader_output == NONE.id
    assert UIA in windows.output_choices()
    assert UIA not in AnnouncementsPreferences(settings, translate, "linux").output_choices()


def test_an_output_that_does_not_exist_here_is_ignored() -> None:
    preferences = AnnouncementsPreferences(
        Settings(screen_reader_output=NONE.id), translate, "linux"
    )
    preferences.select_output(UIA.id)
    assert preferences.screen_reader_output == NONE.id


def test_changing_the_output_is_written_and_said() -> None:
    settings = Settings(screen_reader_output=UIA.id)
    preferences = AnnouncementsPreferences(settings, translate, "win32")
    preferences.select_output(NONE.id)
    changes = preferences.apply()
    assert changes == AppliedChanges(screen_reader_output=True)
    assert settings.screen_reader_output == NONE.id


def test_the_activity_starts_from_the_settings_and_is_written_back() -> None:
    settings = Settings()
    preferences = page(settings)
    assert (preferences.activity_interval, preferences.activity_only_in_output) == (1, True)
    preferences.set_activity_interval(4)
    preferences.activity_only_in_output = False
    assert preferences.apply().announcements
    assert (settings.activity_interval, settings.activity_only_in_output) == (4, False)


def test_an_interval_out_of_range_is_ignored() -> None:
    preferences = page()
    preferences.set_activity_interval(0)
    preferences.set_activity_interval(11)
    assert preferences.activity_interval == 1


def test_nothing_changed_is_no_change() -> None:
    assert not page().apply().announcements


def test_the_activity_category_offers_none_messages_or_beep_and_messages() -> None:
    assert ACTIVITY in CATEGORIES
    assert ACTIVITY.default is Destination.ELEMENT_OR_BEEP
    assert ACTIVITY.choices == (
        Destination.NONE,
        Destination.ELEMENT_OR_BEEP,
        Destination.ELEMENT,
    )
