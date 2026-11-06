"""The beep of the activity, played with ``winsound`` (no file of sound is delivered).

``winsound.Beep`` blocks the thread that calls it for the length of the sound, so it is played from
a worker thread; that thread does not touch ``wx``. See "Shortcuts, announcements, language,
settings" in ``specs/architecture/window.md``.
"""

import logging
import threading
import winsound

logger = logging.getLogger(__name__)

FREQUENCY = 880  # hertz
DURATION_MS = 40


class WinsoundBeeper:
    """Implements :class:`~n5terminal.core.config.announcements.Beeper` for Windows."""

    def beep(self) -> None:
        threading.Thread(target=self._play, name="beep", daemon=True).start()

    @staticmethod
    def _play() -> None:
        try:
            winsound.Beep(FREQUENCY, DURATION_MS)
        except RuntimeError:
            logger.warning("The beep could not be played", exc_info=True)
