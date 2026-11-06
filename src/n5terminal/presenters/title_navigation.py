"""Going from title to title in the output (keys 1 to 6 and T, Shift backwards).

The window gives the text of the output and the caret; this finds the title, says it through the
announcement center and returns where the caret goes. See "Titles" in ``specs/interface.md``.
"""

from n5terminal.core.config.announcements import Announce, Say
from n5terminal.core.config.settings import Settings
from n5terminal.core.screen.titles import next_title, parse_titles, previous_title
from n5terminal.presenters.comfort_reading import comfort_text


def _missing(level: int | None, *, backwards: bool) -> Announce:
    if level is None:
        return Announce.NO_PREVIOUS_TITLE if backwards else Announce.NO_NEXT_TITLE
    if backwards:
        return Announce.NO_PREVIOUS_TITLE_OF_LEVEL
    return Announce.NO_NEXT_TITLE_OF_LEVEL


class TitleNavigator:
    """Finds the title to go to and announces it."""

    def __init__(self, say: Say, settings: Settings | None = None) -> None:
        self._say = say
        self._settings = settings

    def go(self, text: str, position: int, level: int | None, *, backwards: bool) -> int | None:
        """The index in ``text`` of the title reached from ``position``; ``None`` if there is none.

        ``level`` is 1 to 6, or ``None`` for a title of any level.
        """
        titles = parse_titles(text)
        if backwards:
            target = previous_title(titles, position, level)
        else:
            target = next_title(titles, position, level)
        if target is None:
            self._say(_missing(level, backwards=backwards), level=level)
            return None
        title = target.text
        if self._settings is not None and self._settings.comfort_titles:
            # the title of a command, without its prompt
            title = comfort_text(title, self._settings.patterns())
        self._say(Announce.MOVED_TITLE, title=title, level=target.level, line=title)
        return target.start
