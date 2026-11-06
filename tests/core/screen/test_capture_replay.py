"""The replay of a capture through the screen model (``fakes/capture_replay.py``)."""

import math

import pytest

from fakes.capture_replay import TICK, replay
from fakes.captures import load_capture

pytestmark = pytest.mark.unit


def test_there_is_a_step_per_chunk_and_a_last_one_when_the_program_ended() -> None:
    capture = load_capture("progress")
    steps = replay(capture, chunk=8)
    assert len(steps) == math.ceil(len(capture.data) / 8) + 1
    assert [step.number for step in steps] == list(range(1, len(steps) + 1))
    assert not any(step.ended for step in steps[:-1])
    assert steps[-1].ended


def test_the_clock_is_simulated_one_tick_per_step() -> None:
    steps = replay(load_capture("progress"), chunk=8)
    assert [step.time for step in steps] == pytest.approx(
        [TICK * n for n in range(1, len(steps) + 1)]
    )


def test_a_step_tells_whether_the_screen_changed() -> None:
    steps = replay(load_capture("progress"), chunk=8)
    assert [step.number for step in steps if step.changed] == [1, 4, 5, 6]


def test_the_size_of_the_chunk_does_not_change_the_last_screen() -> None:
    capture = load_capture("many_lines")

    def lines(chunk: int) -> list[str]:
        fixed: list[str] = []
        live: dict[int, str] = {}
        for step in replay(capture, chunk=chunk):
            update = step.update
            fixed.extend(line.text for line in update.fixed)
            if update.replace_all:
                live.clear()
            live.update({row.number: row.text for row in update.rows})
        return [*fixed, *(text for _number, text in sorted(live.items()))]

    assert lines(1) == lines(64) == lines(4096)
