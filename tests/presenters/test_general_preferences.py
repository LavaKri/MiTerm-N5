import pytest

from n5terminal.core.config.file_association import FileAssociation
from n5terminal.core.config.settings import Settings
from n5terminal.presenters.general_preferences import (
    MAX_OUTPUT_LIMIT,
    MIN_OUTPUT_LIMIT,
    GeneralPreferences,
)
from n5terminal.presenters.preferences_changes import AppliedChanges

pytestmark = pytest.mark.unit


def test_the_draft_starts_from_the_settings() -> None:
    page = GeneralPreferences(Settings(language="en", output_limit=5_000))
    assert (page.language, page.output_limit) == ("en", 5_000)


def test_each_language_is_named_in_its_own_language() -> None:
    page = GeneralPreferences(Settings())
    assert page.language_choices() == [("fr", "Français"), ("en", "English")]


def test_an_unknown_language_is_ignored() -> None:
    page = GeneralPreferences(Settings())
    page.select_language("de")
    assert page.language == "fr"


def test_the_size_of_the_output_is_brought_into_the_allowed_range() -> None:
    page = GeneralPreferences(Settings())
    assert page.set_output_limit(10) == MIN_OUTPUT_LIMIT
    assert page.set_output_limit(10_000_000) == MAX_OUTPUT_LIMIT
    assert page.set_output_limit(20_000) == 20_000


def test_nothing_changed_writes_nothing_and_says_so() -> None:
    changes = GeneralPreferences(Settings()).apply()
    assert changes == AppliedChanges()
    assert not changes.any


def test_apply_writes_the_draft_and_says_what_changed() -> None:
    settings = Settings()
    page = GeneralPreferences(settings)
    page.select_language("en")
    page.set_output_limit(2_000)
    changes = page.apply()
    assert (settings.language, settings.output_limit) == ("en", 2_000)
    assert changes == AppliedChanges(language=True, output_limit=True)
    assert changes.any


def test_the_maximize_choice_is_drafted_then_written_without_a_change_to_apply_at_once() -> None:
    settings = Settings()
    page = GeneralPreferences(settings)
    assert page.maximize_at_start is True
    page.maximize_at_start = False
    changes = page.apply()
    assert settings.maximize_at_start is False
    assert changes == AppliedChanges()


# The association of the launch files -----------------------------------------------------------


class FakeRegistry:
    def __init__(self) -> None:
        self.keys: dict[str, str] = {}

    def read(self, key: str) -> str | None:
        return self.keys.get(key)

    def write(self, key: str, value: str) -> None:
        self.keys[key] = value

    def delete(self, key: str) -> None:
        self.keys = {k: v for k, v in self.keys.items() if not k.startswith(key)}

    def changed(self) -> None:
        pass


def test_the_button_associates_then_dissociates() -> None:
    page = GeneralPreferences(Settings(), FileAssociation(FakeRegistry(), "cmd"))
    assert page.association_label() == "Associate the .n5term files with MiTerm-N5"
    assert page.toggle_association() == "The .n5term files now open with MiTerm-N5."
    assert page.association_label() == "Remove the association of the .n5term files"
    assert page.toggle_association() == "The .n5term files no longer open with MiTerm-N5."
    assert page.association_label().startswith("Associate")


def test_in_portable_mode_nothing_is_written_and_the_reason_is_told() -> None:
    page = GeneralPreferences(Settings())
    assert page.toggle_association().startswith("Not available in portable mode")
