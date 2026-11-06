"""Replays a capture through the screen model, one chunk per tick of the window.

The bytes of a capture (``tests/data/captures``) are given to ``PyteScreenModel`` in small chunks,
as a transport would, and the update of the screen is taken after each chunk, as the session does at
each tick. The clock is simulated (one tick per chunk), so a replay is the same at every run. Used
by ``tools/replay_screens.py`` and by the tests of the analysis of the lines.
"""

from dataclasses import dataclass

from fakes.captures import Capture
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.screen_model import ScreenUpdate

DEFAULT_CHUNK = 256  # bytes given to the model at a time
TICK = 0.05  # seconds that pass between two chunks: the window takes the output every 50 ms


@dataclass(slots=True, frozen=True)
class ReplayStep:
    """What one chunk made: the update of the screen, and whether the program had ended."""

    number: int
    time: float
    update: ScreenUpdate
    ended: bool

    @property
    def changed(self) -> bool:
        """Did the screen change at this step?"""
        return bool(self.update.fixed or self.update.rows)


def replay(capture: Capture, chunk: int = DEFAULT_CHUNK, tick: float = TICK) -> list[ReplayStep]:
    """The steps of the capture, then a last one when the program ended (the model lets go)."""
    model = PyteScreenModel(capture.columns, capture.rows)
    steps: list[ReplayStep] = []

    def step(ended: bool) -> None:
        number = len(steps) + 1
        steps.append(ReplayStep(number, number * tick, model.take_update(), ended))

    data = capture.data
    for start in range(0, len(data), chunk):
        model.feed(data[start : start + chunk])
        step(ended=False)
    model.finish()
    step(ended=True)
    return steps
