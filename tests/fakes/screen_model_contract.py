"""Contract tests of the screen model: any implementation of ``ScreenModel`` must pass them.

A test file subclasses :class:`ScreenModelContract` and gives ``make_model``. The real captures of
``tests/data/captures`` are replayed and compared with what pyte's own history plus screen holds, so
the reference stays the same whatever implementation runs (pyte now, a native module later).
"""

import pytest

from fakes.captures import capture_names, load_capture
from fakes.screen_mirror import ScreenMirror
from fakes.screen_text import screen_lines
from n5terminal.core.screen.screen_model import ScreenModel
from n5terminal.core.transport.transport import Stream

CSI = "\x1b["


def encode(text: str) -> bytes:
    return text.encode("utf-8")


class ScreenModelContract:
    def make_model(self, columns: int = 80, rows: int = 24) -> ScreenModel:
        raise NotImplementedError

    def shown(self, text: str, columns: int = 80, rows: int = 24) -> ScreenMirror:
        model = self.make_model(columns, rows)
        model.feed(encode(text))
        mirror = ScreenMirror()
        mirror.take(model)
        return mirror

    # Real programs

    @pytest.mark.parametrize("name", capture_names())
    def test_capture_shows_the_lines_pyte_holds(self, name: str) -> None:
        capture = load_capture(name)
        mirror = self.shown(capture.text, capture.columns, capture.rows)
        assert mirror.lines() == screen_lines(capture.text, capture.columns, capture.rows)

    @pytest.mark.parametrize("size", [1, 7, 4096])
    @pytest.mark.parametrize("name", capture_names())
    def test_capture_fed_in_pieces_gives_the_same_lines(self, name: str, size: int) -> None:
        capture = load_capture(name)
        model = self.make_model(capture.columns, capture.rows)
        mirror = ScreenMirror()
        data = capture.data
        for start in range(0, len(data), size):
            model.feed(data[start : start + size])
            mirror.take(model)
        assert mirror.lines() == screen_lines(capture.text, capture.columns, capture.rows)

    # Size and updates

    def test_size_is_the_one_asked(self) -> None:
        model = self.make_model(100, 30)
        assert (model.columns, model.row_count) == (100, 30)

    def test_first_update_holds_every_row(self) -> None:
        model = self.make_model(80, 24)
        update = model.take_update()
        assert update.replace_all
        assert [row.number for row in update.rows] == list(range(24))
        assert update.fixed == ()

    def test_update_without_change_is_empty(self) -> None:
        model = self.make_model()
        model.feed(encode("hello"))
        model.take_update()
        update = model.take_update()
        assert not update.replace_all
        assert update.rows == ()
        assert update.fixed == ()
        assert update.overflows == ()

    def test_update_carries_the_changed_rows_only(self) -> None:
        model = self.make_model()
        model.feed(encode("first\r\nsecond"))
        model.take_update()
        model.feed(encode("!"))
        update = model.take_update()
        assert not update.replace_all
        assert [(row.number, row.text) for row in update.rows] == [(1, "second!")]

    def test_a_row_written_again_with_the_same_text_is_not_reported(self) -> None:
        model = self.make_model()
        model.feed(encode("same"))
        model.take_update()
        model.feed(encode("\rsame"))
        assert model.take_update().rows == ()

    def test_most_rows_changed_replaces_the_live_part(self) -> None:
        model = self.make_model(80, 4)
        model.feed(encode("a\r\nb\r\nc"))
        model.take_update()
        model.feed(encode(f"{CSI}2J"))
        update = model.take_update()
        assert update.replace_all
        assert [row.text for row in update.rows] == ["", "", "", ""]

    def test_trailing_blanks_are_removed(self) -> None:
        mirror = self.shown("word   ")
        assert mirror.rows[0].text == "word"

    def test_cursor_follows_the_text(self) -> None:
        model = self.make_model()
        model.feed(encode("ab\r\ncde"))
        update = model.take_update()
        assert (update.cursor_row, update.cursor_column) == (1, 3)

    def test_resize_replaces_the_live_part(self) -> None:
        model = self.make_model(80, 24)
        model.feed(encode("text"))
        model.take_update()
        model.resize(100, 30)
        update = model.take_update()
        assert update.replace_all
        assert (update.columns, update.row_count) == (100, 30)
        assert [row.number for row in update.rows] == list(range(30))
        assert update.rows[0].text == "text"

    # Fixed lines

    def test_lines_leaving_the_screen_become_fixed_lines(self) -> None:
        text = "".join(f"line {number}\r\n" for number in range(1, 31))
        mirror = self.shown(text, 80, 24)
        assert [line.text for line in mirror.fixed] == [f"line {n}" for n in range(1, 8)]
        assert mirror.lines() == [f"line {n}" for n in range(1, 31)]

    def test_fixed_lines_come_once_and_in_order(self) -> None:
        model = self.make_model(80, 3)
        mirror = ScreenMirror()
        for number in range(1, 9):
            model.feed(encode(f"line {number}\r\n"))
            mirror.take(model)
        assert [line.text for line in mirror.fixed] == [f"line {n}" for n in range(1, 7)]
        assert model.take_update().fixed == ()

    def test_clearing_the_screen_keeps_the_fixed_lines(self) -> None:
        text = "".join(f"line {number}\r\n" for number in range(1, 31)) + f"{CSI}2J{CSI}Hnew"
        mirror = self.shown(text, 80, 24)
        assert mirror.lines()[-1] == "new"
        assert len(mirror.fixed) == 7

    # Decoding

    def test_character_split_between_two_feeds(self) -> None:
        model = self.make_model()
        data = encode("café")
        model.feed(data[:4])
        model.feed(data[4:])
        mirror = ScreenMirror()
        mirror.take(model)
        assert mirror.lines() == ["café"]

    def test_sequence_split_between_two_feeds(self) -> None:
        model = self.make_model()
        model.feed(encode("ab\x1b[1"))
        model.feed(encode("Dc"))
        mirror = ScreenMirror()
        mirror.take(model)
        assert mirror.lines() == ["ac"]

    def test_invalid_bytes_are_replaced(self) -> None:
        model = self.make_model()
        model.feed(b"a\xffb")
        mirror = ScreenMirror()
        mirror.take(model)
        assert mirror.lines() == ["a�b"]

    def test_wide_characters_read_as_written(self) -> None:
        assert self.shown("漢字 ok").lines() == ["漢字 ok"]

    def test_carriage_return_rewrites_the_line(self) -> None:
        assert self.shown("10%\r50%\r100%").lines() == ["100%"]

    # Lines longer than the screen

    def test_wrapped_rows_are_continued(self) -> None:
        mirror = self.shown("x" * 200)
        assert [mirror.rows[number].text for number in range(3)] == ["x" * 80, "x" * 80, "x" * 40]
        assert [mirror.rows[number].continued for number in range(3)] == [True, True, False]

    def test_line_of_the_screen_width_is_not_continued(self) -> None:
        mirror = self.shown("x" * 80 + "\r\nnext")
        assert not mirror.rows[0].continued
        assert mirror.overflows == []

    def test_line_ends_with_the_excess_beyond_the_screen(self) -> None:
        mirror = self.shown("x" * 200 + "\r\n")
        assert mirror.overflows == [120]

    def test_line_not_ended_yet_is_not_reported(self) -> None:
        mirror = self.shown("x" * 200)
        assert mirror.overflows == []

    def test_excess_counts_over_several_feeds(self) -> None:
        model = self.make_model()
        mirror = ScreenMirror()
        for piece in ("x" * 70, "x" * 20, "x" * 10, "\r\n"):
            model.feed(encode(piece))
            mirror.take(model)
        assert mirror.overflows == [20]

    def test_each_wrapped_line_is_reported(self) -> None:
        mirror = self.shown("x" * 83 + "\r\n" + "y" * 81 + "\r\nshort\r\n")
        assert mirror.overflows == [3, 1]

    def test_cursor_move_ends_the_line(self) -> None:
        mirror = self.shown("x" * 90 + f"{CSI}5;1Hnext")
        assert mirror.overflows == [10]

    def test_wrapped_line_leaving_the_screen_stays_continued(self) -> None:
        text = "x" * 170 + "\r\n" + "".join(f"line {n}\r\n" for n in range(1, 30))
        mirror = self.shown(text, 80, 24)
        assert [line.continued for line in mirror.fixed[:4]] == [True, True, False, False]

    def test_erased_row_is_no_longer_continued(self) -> None:
        mirror = self.shown("x" * 100 + f"{CSI}1;1H{CSI}K")
        assert not mirror.rows[0].continued

    def test_rewritten_row_is_no_longer_continued(self) -> None:
        mirror = self.shown("x" * 100 + f"{CSI}1;1Hshort{CSI}K")
        assert mirror.rows[0].text == "short"
        assert not mirror.rows[0].continued

    def test_a_row_wrapped_before_a_widening_stays_continued(self) -> None:
        model = self.make_model(80, 24)
        model.feed(encode("x" * 100))
        model.take_update()
        model.resize(120, 30)
        update = model.take_update()
        assert [row.continued for row in update.rows[:2]] == [True, False]
        assert update.rows[0].text == "x" * 80

    def test_a_row_wrapped_then_erased_after_a_widening_is_not_continued(self) -> None:
        model = self.make_model(80, 24)
        model.feed(encode("x" * 100))
        model.take_update()
        model.resize(120, 30)
        model.feed(encode(f"{CSI}1;1H{CSI}K"))
        update = model.take_update()
        assert not update.rows[0].continued

    # What the session asks of a model beyond the screen

    def test_the_cursor_keys_are_not_in_application_mode_at_first(self) -> None:
        assert not self.make_model().application_cursor_keys

    def test_the_cursor_keys_follow_the_mode_the_program_asks_for(self) -> None:
        model = self.make_model()
        model.feed(encode(f"{CSI}?1h"))
        assert model.application_cursor_keys
        model.feed(encode(f"{CSI}?1l"))
        assert not model.application_cursor_keys

    def test_the_mode_of_the_cursor_keys_can_come_in_two_pieces(self) -> None:
        model = self.make_model()
        model.feed(encode(f"{CSI}?"))
        model.feed(encode("1h"))
        assert model.application_cursor_keys

    def test_the_stream_of_the_bytes_is_taken(self) -> None:
        model = self.make_model()
        model.feed(encode("out "), Stream.OUTPUT)
        model.feed(encode("err"), Stream.ERROR)
        mirror = ScreenMirror()
        mirror.take(model)
        assert mirror.lines() == ["out err"]

    def test_finishing_keeps_what_the_program_left_on_the_screen(self) -> None:
        model = self.make_model()
        model.feed(encode("first\r\nsecond"))
        mirror = ScreenMirror()
        mirror.take(model)
        model.finish()
        mirror.take(model)
        assert mirror.lines() == ["first", "second"]

    def test_finishing_without_output_changes_nothing(self) -> None:
        model = self.make_model()
        model.finish()
        update = model.take_update()
        assert update.fixed == ()
        assert not any(row.text for row in update.rows)
