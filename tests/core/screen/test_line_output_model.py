import pytest

from fakes.screen_mirror import ScreenMirror
from n5terminal.core.screen.line_output_model import LineOutputModel
from n5terminal.core.screen.output_filter import CarriageReturnPolicy, FilterRules
from n5terminal.core.transport.transport import Stream

pytestmark = pytest.mark.unit


def shown(*pieces: bytes, model: LineOutputModel | None = None) -> ScreenMirror:
    model = model or LineOutputModel()
    mirror = ScreenMirror()
    for piece in pieces:
        model.feed(piece)
        mirror.take(model)
    return mirror


def test_size_is_one_row_without_width() -> None:
    model = LineOutputModel()
    assert (model.columns, model.row_count) == (0, 1)


def test_finished_lines_are_fixed_and_the_unfinished_one_is_live() -> None:
    mirror = shown(b"first\nsecond\nthi")
    assert [line.text for line in mirror.fixed] == ["first", "second"]
    assert mirror.rows[0].text == "thi"
    assert mirror.lines() == ["first", "second", "thi"]


def test_a_line_finished_later_moves_to_the_fixed_part() -> None:
    mirror = shown(b"par", b"tial\n", b"next")
    assert [line.text for line in mirror.fixed] == ["partial"]
    assert mirror.lines() == ["partial", "next"]


def test_a_blank_line_is_kept() -> None:
    assert shown(b"a\n\nb\n").lines() == ["a", "", "b"]


def test_crlf_is_one_line_break() -> None:
    assert shown(b"a\r\nb\r\n").lines() == ["a", "b"]


def test_a_progress_bar_keeps_the_last_state_of_its_line() -> None:
    mirror = shown(b"10%", b"\r50%", b"\r100%\n", b"done\n")
    assert mirror.lines() == ["100%", "done"]


def test_a_progress_bar_is_a_live_row_until_it_ends() -> None:
    model = LineOutputModel()
    mirror = ScreenMirror()
    model.feed(b"10%")
    mirror.take(model)
    model.feed(b"\r20%")
    update = mirror.take(model)
    assert update.fixed == ()
    assert [row.text for row in update.rows] == ["20%"]


def test_nothing_new_gives_an_empty_update() -> None:
    model = LineOutputModel()
    model.feed(b"abc")
    model.take_update()
    update = model.take_update()
    assert (update.fixed, update.rows, update.replace_all) == ((), (), False)


def test_the_first_update_holds_the_live_row() -> None:
    update = LineOutputModel().take_update()
    assert [row.text for row in update.rows] == [""]
    assert update.replace_all


def test_escape_sequences_are_removed() -> None:
    assert shown(b"\x1b[31mred\x1b[0m\n").lines() == ["red"]


def test_utf8_split_between_two_blocks() -> None:
    data = "café\n".encode()
    assert shown(data[:4], data[4:]).lines() == ["café"]


def test_old_code_page_programs_are_read_with_the_fallback() -> None:
    assert shown("été\n".encode("cp850")).lines() == ["été"]


def test_rules_can_be_changed() -> None:
    model = LineOutputModel(FilterRules(carriage_return=CarriageReturnPolicy.NEW_LINE))
    assert shown(b"a\rb\n", model=model).lines() == ["a", "b"]


def test_a_very_long_line_is_cut_and_marked_continued() -> None:
    mirror = shown(b"x" * 25 + b"\n", model=LineOutputModel(max_line_length=10))
    assert [(line.text, line.continued) for line in mirror.fixed] == [
        ("x" * 10, True),
        ("x" * 10, True),
        ("x" * 5, False),
    ]


def test_an_unfinished_long_line_is_cut_too() -> None:
    mirror = shown(b"x" * 25, model=LineOutputModel(max_line_length=10))
    assert len(mirror.fixed) == 2
    assert mirror.rows[0].text == "x" * 5


def test_the_two_streams_come_in_arrival_order() -> None:
    model = LineOutputModel()
    model.feed(b"out 1\n", Stream.OUTPUT)
    model.feed(b"err 1\n", Stream.ERROR)
    model.feed(b"out 2\n", Stream.OUTPUT)
    mirror = ScreenMirror()
    mirror.take(model)
    assert mirror.lines() == ["out 1", "StdErr: err 1", "out 2"]


def test_a_line_is_never_shared_by_the_two_streams() -> None:
    model = LineOutputModel()
    model.feed(b"out", Stream.OUTPUT)
    model.feed(b"err\n", Stream.ERROR)
    model.feed(b" more\n", Stream.OUTPUT)
    mirror = ScreenMirror()
    mirror.take(model)
    assert mirror.lines() == ["out", "StdErr: err", " more"]


def _error_lines(*pieces: bytes) -> list[str]:
    model = LineOutputModel()
    mirror = ScreenMirror()
    for piece in pieces:
        model.feed(piece, Stream.ERROR)
        mirror.take(model)
    return mirror.lines()


def test_each_line_of_the_standard_error_starts_with_the_mark_once() -> None:
    assert _error_lines(b"one\ntw", b"o\nthree\n") == [
        "StdErr: one",
        "StdErr: two",
        "StdErr: three",
    ]


def test_a_progress_bar_on_the_standard_error_is_marked_once() -> None:
    assert _error_lines(b"10%", b"\r50%", b"\r100%\n", b"done\n") == [
        "StdErr: 100%",
        "StdErr: done",
    ]


def test_a_blank_line_of_the_standard_error_is_not_marked() -> None:
    assert _error_lines(b"a\n\nb\n") == ["StdErr: a", "", "StdErr: b"]


def test_the_standard_error_is_not_marked_when_the_mark_is_off() -> None:
    model = LineOutputModel(mark_stderr=False)
    mirror = ScreenMirror()
    model.feed(b"err\n", Stream.ERROR)
    mirror.take(model)
    assert mirror.lines() == ["err"]


def test_the_standard_output_is_not_marked() -> None:
    assert shown(b"text\n").lines() == ["text"]


def test_finish_releases_a_sequence_cut_at_the_end() -> None:
    model = LineOutputModel()
    model.feed(b"text\x1b[3")
    model.finish()
    mirror = ScreenMirror()
    mirror.take(model)
    assert mirror.lines() == ["text"]


def test_a_model_without_a_terminal_never_has_the_cursor_keys_in_application_mode() -> None:
    model = LineOutputModel()
    model.feed(b"\x1b[?1h")
    assert not model.application_cursor_keys
