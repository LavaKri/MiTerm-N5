import threading

import pytest

from fakes.captures import capture_names, load_capture
from fakes.screen_mirror import ScreenMirror
from fakes.screen_text import screen_lines
from n5terminal.core.screen.display_exchange import DisplayExchange, ScreenPump
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel
from n5terminal.core.screen.screen_model import FixedLine, ScreenRow, ScreenUpdate
from n5terminal.core.transport.transport import Stream


def update(
    fixed: tuple[str, ...] = (),
    rows: tuple[tuple[int, str], ...] = (),
    replace_all: bool = False,
    overflows: tuple[int, ...] = (),
    cursor_row: int = 0,
) -> ScreenUpdate:
    return ScreenUpdate(
        fixed=tuple(FixedLine(text) for text in fixed),
        rows=tuple(ScreenRow(number, text) for number, text in rows),
        replace_all=replace_all,
        overflows=overflows,
        columns=80,
        row_count=24,
        cursor_row=cursor_row,
        cursor_column=0,
    )


@pytest.mark.unit
class TestDisplayExchange:
    def test_nothing_published_gives_nothing(self) -> None:
        assert DisplayExchange().take() is None

    def test_taken_once(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(fixed=("a",)))
        assert exchange.take() is not None
        assert exchange.take() is None

    def test_fixed_lines_accumulate_in_order(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(fixed=("a", "b")))
        exchange.publish(update(fixed=("c",)))
        batch = exchange.take()
        assert batch is not None
        assert [line.text for line in batch.update.fixed] == ["a", "b", "c"]
        assert batch.dropped_lines == 0

    def test_only_the_latest_state_of_a_row_is_kept(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(rows=((2, "old"), (5, "five"))))
        exchange.publish(update(rows=((2, "new"),)))
        batch = exchange.take()
        assert batch is not None
        assert [(row.number, row.text) for row in batch.update.rows] == [(2, "new"), (5, "five")]
        assert not batch.update.replace_all

    def test_replacement_then_changes_is_one_replacement_with_every_row(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(rows=((0, "stale"), (3, "gone"))))
        exchange.publish(update(rows=((0, "a"), (1, "b")), replace_all=True))
        exchange.publish(update(rows=((1, "B"),)))
        batch = exchange.take()
        assert batch is not None
        assert batch.update.replace_all
        assert [(row.number, row.text) for row in batch.update.rows] == [(0, "a"), (1, "B")]

    def test_replacement_is_forgotten_once_taken(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(rows=((0, "a"),), replace_all=True))
        exchange.take()
        exchange.publish(update(rows=((0, "b"),)))
        batch = exchange.take()
        assert batch is not None
        assert not batch.update.replace_all

    def test_overflows_accumulate_and_the_cursor_is_the_latest(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(overflows=(3,), cursor_row=1))
        exchange.publish(update(overflows=(11, 4), cursor_row=7))
        batch = exchange.take()
        assert batch is not None
        assert batch.update.overflows == (3, 11, 4)
        assert batch.update.cursor_row == 7

    def test_oldest_fixed_lines_are_dropped_past_the_limit_and_counted(self) -> None:
        exchange = DisplayExchange(max_fixed_lines=3)
        exchange.publish(update(fixed=("1", "2", "3", "4")))
        exchange.publish(update(fixed=("5", "6")))
        batch = exchange.take()
        assert batch is not None
        assert [line.text for line in batch.update.fixed] == ["4", "5", "6"]
        assert batch.dropped_lines == 3
        exchange.publish(update(fixed=("7",)))
        again = exchange.take()
        assert again is not None
        assert again.dropped_lines == 0


@pytest.mark.unit
class TestScreenPump:
    @pytest.mark.parametrize("name", capture_names())
    def test_blocks_taken_at_any_moment_give_the_lines_pyte_holds(self, name: str) -> None:
        capture = load_capture(name)
        exchange = DisplayExchange()
        pump = ScreenPump(PyteScreenModel(capture.columns, capture.rows), exchange, block_size=5)
        mirror = ScreenMirror()
        data = capture.data
        for number, start in enumerate(range(0, len(data), 23)):
            pump.feed(data[start : start + 23])
            batch = exchange.take() if number % 3 == 0 else None
            if batch is not None:
                mirror.apply(batch.update)
        batch = exchange.take()
        if batch is not None:
            mirror.apply(batch.update)
        assert mirror.lines() == screen_lines(capture.text, capture.columns, capture.rows)

    def test_resize_reaches_the_ui_as_a_replacement(self) -> None:
        exchange = DisplayExchange()
        pump = ScreenPump(PyteScreenModel(80, 24), exchange)
        pump.feed(b"text")
        exchange.take()
        pump.resize(100, 30)
        batch = exchange.take()
        assert batch is not None
        assert batch.update.replace_all
        assert (batch.update.columns, batch.update.row_count) == (100, 30)

    def test_the_stream_reaches_the_model_and_the_end_is_told_to_it(self) -> None:
        calls: list[tuple[str, int, Stream | None]] = []

        class Recording(PyteScreenModel):
            def feed(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
                calls.append(("feed", len(data), stream))
                super().feed(data, stream)

            def finish(self) -> None:
                calls.append(("finish", 0, None))
                super().finish()

        pump = ScreenPump(Recording(), DisplayExchange(), block_size=4)
        pump.feed(b"abcdefgh!", Stream.ERROR)
        pump.finish()
        assert calls == [
            ("feed", 4, Stream.ERROR),
            ("feed", 4, Stream.ERROR),
            ("feed", 1, Stream.ERROR),
            ("finish", 0, None),
        ]

    def test_the_cursor_keys_mode_is_the_one_of_the_model(self) -> None:
        pump = ScreenPump(PyteScreenModel(), DisplayExchange())
        assert not pump.application_cursor_keys
        pump.feed(b"\x1b[?1h")
        assert pump.application_cursor_keys

    def test_nothing_fed_publishes_nothing(self) -> None:
        exchange = DisplayExchange()
        ScreenPump(PyteScreenModel(), exchange).feed(b"")
        assert exchange.take() is None


@pytest.mark.slow
def test_a_flood_fed_while_the_ui_takes_loses_nothing() -> None:
    lines = 20_000
    exchange = DisplayExchange(max_fixed_lines=lines)
    pump = ScreenPump(PyteScreenModel(80, 24), exchange)
    data = "".join(f"line {number}\r\n" for number in range(lines)).encode("ascii")

    def feed_all() -> None:
        for start in range(0, len(data), 4096):
            pump.feed(data[start : start + 4096])

    feeder = threading.Thread(target=feed_all)
    mirror = ScreenMirror()
    feeder.start()
    while feeder.is_alive():
        batch = exchange.take()
        if batch is not None:
            mirror.apply(batch.update)
    feeder.join()
    batch = exchange.take()
    if batch is not None:
        mirror.apply(batch.update)
    assert mirror.lines() == [f"line {number}" for number in range(lines)]


def closing_only(*lines: str) -> ScreenUpdate:
    """What the session publishes at the end of a connection: it says nothing of the screen."""
    return ScreenUpdate(
        fixed=(),
        rows=(),
        replace_all=False,
        overflows=(),
        columns=0,
        row_count=0,
        cursor_row=0,
        cursor_column=0,
        closing=tuple(FixedLine(text) for text in lines),
    )


@pytest.mark.unit
class TestClosingPart:
    def test_nothing_is_closing_unless_someone_says_so(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(update(fixed=("a",)))
        batch = exchange.take()
        assert batch is not None
        assert batch.update.closing is None

    def test_the_closing_lines_reach_the_ui_once(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(closing_only("Closed."))
        first, second = exchange.take(), exchange.take()
        assert first is not None
        assert first.update.closing == (FixedLine("Closed."),)
        assert second is None

    def test_the_latest_word_on_the_closing_part_is_the_one_kept(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(closing_only("one"))
        exchange.publish(closing_only("two"))
        exchange.publish(update(fixed=("a",)))  # an update that says nothing of it changes nothing
        batch = exchange.take()
        assert batch is not None
        assert batch.update.closing == (FixedLine("two"),)

    def test_an_empty_closing_part_is_a_word_too(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(closing_only("one"))
        exchange.publish(closing_only())
        batch = exchange.take()
        assert batch is not None
        assert batch.update.closing == ()

    def test_the_screen_of_the_batch_is_the_last_that_told_one(self) -> None:
        """The update of the closing part has no cursor: the cursor of the screen is not lost."""
        exchange = DisplayExchange()
        exchange.publish(update(rows=((0, "x"),), cursor_row=5))
        exchange.publish(closing_only("Closed."))
        batch = exchange.take()
        assert batch is not None
        assert (batch.update.columns, batch.update.row_count, batch.update.cursor_row) == (
            80,
            24,
            5,
        )
        assert batch.update.closing == (FixedLine("Closed."),)

    def test_a_batch_of_the_closing_part_alone_has_no_screen_to_tell(self) -> None:
        exchange = DisplayExchange()
        exchange.publish(closing_only("Closed."))
        batch = exchange.take()
        assert batch is not None
        assert batch.update.row_count == 0
