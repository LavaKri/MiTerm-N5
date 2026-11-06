"""What the Preferences changed, so that the window can apply at once what can be."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AppliedChanges:
    """The settings the user changed in the Preferences, by subject."""

    language: bool = False
    screen_reader_output: bool = False
    output_limit: bool = False
    announcements: bool = False
    shortcuts: bool = False

    @property
    def any(self) -> bool:
        return (
            self.language
            or self.screen_reader_output
            or self.output_limit
            or self.announcements
            or self.shortcuts
        )

    def merged(self, other: AppliedChanges) -> AppliedChanges:
        """The changes of both."""
        return AppliedChanges(
            language=self.language or other.language,
            screen_reader_output=self.screen_reader_output or other.screen_reader_output,
            output_limit=self.output_limit or other.output_limit,
            announcements=self.announcements or other.announcements,
            shortcuts=self.shortcuts or other.shortcuts,
        )
