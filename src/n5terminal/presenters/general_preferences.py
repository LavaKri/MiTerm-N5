"""The General page of the Preferences: the language and the number of lines of the output.

See "Preferences" in ``specs/interface.md``. The page edits a draft; ``apply`` writes it to the
settings and says what changed, so that the window can apply at once what can be.
"""

from collections.abc import Sequence

from n5terminal.core.config.file_association import FileAssociation
from n5terminal.core.config.launch_file import LAUNCH_FILE_EXTENSION
from n5terminal.core.config.settings import OUTPUT_LIMITS, SUPPORTED_LANGUAGES, Settings
from n5terminal.i18n import N_
from n5terminal.presenters.choices import Translate
from n5terminal.presenters.preferences_changes import AppliedChanges

#: Each language is written in its own language, whatever the language of the application.
LANGUAGE_NAMES = {"fr": "Français", "en": "English"}
MIN_OUTPUT_LIMIT = OUTPUT_LIMITS.start
MAX_OUTPUT_LIMIT = OUTPUT_LIMITS.stop - 1
_FREE_PROFILE = N_("Free")
_ASSOCIATE = N_("Associate the {extension} files with MiTerm-N5")
_DISSOCIATE = N_("Remove the association of the {extension} files")
_ASSOCIATED = N_("The {extension} files now open with MiTerm-N5.")
_DISSOCIATED = N_("The {extension} files no longer open with MiTerm-N5.")
_PORTABLE = N_("Not available in portable mode: it would leave a trace on this computer.")


class GeneralPreferences:
    """The draft of the General page, started from ``settings``."""

    def __init__(
        self,
        settings: Settings,
        association: FileAssociation | None = None,
        translate: Translate = lambda text: text,
        profile_names: Sequence[str] = (),
    ) -> None:
        self._settings = settings
        self._association = association  # None: portable mode, nothing may be written
        self._translate = translate
        self.language = settings.language
        self.output_limit = settings.output_limit
        self.maximize_at_start = settings.maximize_at_start
        self._profile_names = list(profile_names)
        # A profile that no longer exists is shown as the free profile, which the start falls back
        # on; it is only forgotten if the user chooses again (the profiles may be unreadable now).
        self._startup_chosen = False
        self.startup_profile = (
            settings.startup_profile if settings.startup_profile in self._profile_names else ""
        )

    def profile_choices(self) -> list[tuple[str, str]]:
        """The (name, label) of each profile to start on: the free profile (empty name) first."""
        free = ("", self._translate(_FREE_PROFILE))
        return [free, *((name, name) for name in self._profile_names)]

    def select_startup_profile(self, name: str) -> None:
        """Choose the profile to start on; a name that is not a profile is ignored."""
        if name == "" or name in self._profile_names:
            self.startup_profile = name
            self._startup_chosen = True

    def language_choices(self) -> list[tuple[str, str]]:
        """The (code, name) of each language."""
        return [(code, LANGUAGE_NAMES.get(code, code)) for code in SUPPORTED_LANGUAGES]

    def select_language(self, code: str) -> None:
        """Choose a language; an unknown code is ignored."""
        if code in SUPPORTED_LANGUAGES:
            self.language = code

    def set_output_limit(self, lines: int) -> int:
        """Choose the number of lines the output keeps, brought into the allowed range."""
        self.output_limit = min(max(lines, MIN_OUTPUT_LIMIT), MAX_OUTPUT_LIMIT)
        return self.output_limit

    def apply(self) -> AppliedChanges:
        """Write the draft to the settings (not to the file) and tell what was different."""
        settings = self._settings
        changes = AppliedChanges(
            language=self.language != settings.language,
            output_limit=self.output_limit != settings.output_limit,
        )
        settings.language = self.language
        settings.output_limit = self.output_limit
        settings.maximize_at_start = self.maximize_at_start  # read at the next start
        if self._startup_chosen:
            settings.startup_profile = self.startup_profile  # read at the next start
        return changes

    # The association of the launch files, done at once (not a draft) ----------------------------

    def association_label(self) -> str:
        """The text of the button: what it does now."""
        associated = self._association is not None and self._association.is_associated()
        text = self._translate(_DISSOCIATE if associated else _ASSOCIATE)
        return text.format(extension=LAUNCH_FILE_EXTENSION)

    def toggle_association(self) -> str:
        """Associate the launch files, or dissociate them if they are; the message to tell.

        Raises ``AssociationError`` when the registry refuses.
        """
        if self._association is None:
            return self._translate(_PORTABLE)
        if self._association.is_associated():
            self._association.dissociate()
            done = _DISSOCIATED
        else:
            self._association.associate()
            done = _ASSOCIATED
        return self._translate(done).format(extension=LAUNCH_FILE_EXTENSION)
