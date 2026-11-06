import pytest

from n5terminal.core.screen.screen_model import FixedLine, ScreenRow, ScreenUpdate
from n5terminal.presenters.output_text import OutputEdit, OutputText

pytestmark = pytest.mark.unit


def update(
    fixed: tuple[str, ...] = (),
    rows: tuple[tuple[int, str], ...] = (),
    *,
    replace_all: bool = False,
    columns: int = 0,
    row_count: int = 1,
    cursor: tuple[int, int] = (0, 0),
) -> ScreenUpdate:
    return ScreenUpdate(
        fixed=tuple(FixedLine(text) for text in fixed),
        rows=tuple(ScreenRow(number, text) for number, text in rows),
        replace_all=replace_all,
        overflows=(),
        columns=columns,
        row_count=row_count,
        cursor_row=cursor[0],
        cursor_column=cursor[1],
    )


def apply_edit(old: str, edit: OutputEdit) -> str:
    """What the text control does with an edit."""
    new = old[: edit.start] + edit.replacement + old[edit.end :]
    return new[edit.removed_head :]


def play(output: OutputText, *updates: ScreenUpdate) -> str:
    """Apply the updates the way the control does and check the edits give the text kept."""
    control = output.text
    for item in updates:
        edit = output.apply(item)
        if edit is not None:
            control = apply_edit(control, edit)
        assert control == output.text
    return control


def test_fixed_lines_come_before_the_live_line() -> None:
    output = OutputText(100)
    text = play(output, update(("one", "two"), ((0, "thr"),), replace_all=True))
    assert text == "one\ntwo\nthr"


def test_a_progress_bar_changes_only_what_differs() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "10%"),), replace_all=True))
    edit = output.apply(update((), ((0, "20%"),), replace_all=True))
    assert edit is not None
    assert (edit.start, edit.end, edit.replacement) == (0, 1, "2")


def test_the_same_update_again_changes_nothing() -> None:
    output = OutputText(100)
    output.apply(update(("a",), ((0, "b"),), replace_all=True))
    assert output.apply(update((), ((0, "b"),), replace_all=True)) is None
    assert output.apply(update()) is None


def test_a_line_that_ends_only_adds_the_line_break() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "partial"),), replace_all=True))
    edit = output.apply(update(("partial",), ((0, ""),), replace_all=True))
    assert edit is not None
    assert (edit.start, edit.end, edit.replacement) == (7, 7, "\n")
    assert output.text == "partial\n"


def test_the_oldest_lines_are_dropped_past_the_limit_and_counted() -> None:
    output = OutputText(3)
    text = play(output, update(("a", "b", "c", "d", "e"), ((0, "x"),), replace_all=True))
    assert text == "c\nd\ne\nx"
    again = output.apply(update(("f",), ((0, "x"),), replace_all=True))
    assert again is not None
    assert (again.trimmed_lines, again.removed_head) == (1, 2)
    assert output.text == "d\ne\nf\nx"


def test_edits_always_give_the_text_that_is_kept() -> None:
    output = OutputText(4)
    updates = [update((f"line {n}",), ((0, f"live {n}"),), replace_all=True) for n in range(12)]
    assert play(output, *updates).startswith("line 8\n")


def test_a_terminal_replaces_its_rows_and_hides_the_blank_ones_at_the_end() -> None:
    output = OutputText(100)
    rows = tuple((n, "") for n in range(5))
    text = play(output, update((), rows, replace_all=True, columns=80, row_count=5))
    assert text == ""
    text = play(output, update((), ((0, "$ ls"), (1, "file")), columns=80, row_count=5))
    assert text == "$ ls\nfile"
    text = play(output, update((), ((1, "other"),), columns=80, row_count=5))
    assert text == "$ ls\nother"


def test_rows_in_the_middle_stay_blank_lines() -> None:
    output = OutputText(100)
    text = play(
        output, update((), ((0, "top"), (2, "end")), replace_all=True, columns=80, row_count=3)
    )
    assert text == "top\n\nend"


def test_without_history_a_terminal_keeps_none_of_its_fixed_lines_and_shows_every_row() -> None:
    output = OutputText(100, show_history=False)
    text = play(
        output,
        update(("gone",), ((0, "a"),), replace_all=True, columns=80, row_count=3),
    )
    assert text == "a\n\n"


def test_without_history_pipes_still_keep_their_lines() -> None:
    output = OutputText(100, show_history=False)
    assert play(output, update(("kept",), ((0, "x"),), replace_all=True)) == "kept\nx"


def test_changing_the_display_rewrites_the_live_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "a"),), replace_all=True, columns=80, row_count=3))
    edit = output.set_show_history(False)
    assert edit is not None
    assert output.text == "a\n\n"
    assert output.set_show_history(False) is None


def test_clear_empties_everything() -> None:
    output = OutputText(100)
    play(output, update(("a", "b"), ((0, "c"),), replace_all=True))
    edit = output.clear()
    assert edit is not None
    assert (edit.start, edit.end, edit.replacement) == (0, 5, "")
    assert output.text == ""
    assert output.clear() is None


# The caret ---------------------------------------------------------------------------------------


def test_a_caret_before_the_change_does_not_move() -> None:
    output = OutputText(100)
    play(output, update(("one", "two"), ((0, "x"),), replace_all=True))
    edit = output.apply(update(("three",), ((0, "y"),), replace_all=True))
    assert edit is not None
    assert output.caret_after(2, edit) == 2  # in "one"


def test_a_caret_in_the_fixed_part_stays_while_lines_arrive() -> None:
    output = OutputText(100)
    play(output, update(("one", "two"), ((0, ""),), replace_all=True))
    edit = output.apply(update(("three", "four"), ((0, ""),), replace_all=True))
    assert edit is not None
    assert output.caret_after(5, edit) == 5  # "t|wo"


def test_a_caret_after_the_change_is_shifted() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "ab"), (1, "cd")), replace_all=True, columns=80, row_count=2))
    edit = output.apply(update((), ((0, "abXX"),), columns=80, row_count=2))
    assert edit is not None
    assert output.text == "abXX\ncd"
    assert output.caret_after(4, edit) == 6  # "c|d": two characters were inserted before it


def test_a_caret_inside_a_rewritten_line_keeps_its_column() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "abcdef"),), replace_all=True))
    edit = output.apply(update((), ((0, "abXdef"),), replace_all=True))
    assert edit is not None
    assert output.caret_after(4, edit) == 4


def test_a_caret_whose_column_disappeared_goes_to_the_start_of_the_line() -> None:
    output = OutputText(100)
    play(output, update(("first",), ((0, "abcdef"),), replace_all=True))
    old_caret = len("first\n") + 5
    edit = output.apply(update((), ((0, "abc"),), replace_all=True))
    assert edit is not None
    assert output.caret_after(old_caret, edit) == len("first\n")


def test_a_caret_follows_the_text_when_the_oldest_lines_are_dropped() -> None:
    output = OutputText(2)
    play(output, update(("a", "b"), ((0, ""),), replace_all=True))
    old_text = output.text  # "a\nb\n"
    edit = output.apply(update(("c",), ((0, ""),), replace_all=True))
    assert edit is not None
    caret = old_text.index("b")
    assert output.text[output.caret_after(caret, edit)] == "b"


def test_a_caret_in_the_dropped_lines_goes_to_the_start() -> None:
    output = OutputText(1)
    play(output, update(("a",), ((0, ""),), replace_all=True))
    edit = output.apply(update(("b",), ((0, ""),), replace_all=True))
    assert edit is not None
    assert output.caret_after(0, edit) == 0


# The terminal cursor -----------------------------------------------------------------------------


def test_the_terminal_cursor_is_in_the_live_part_after_the_fixed_lines() -> None:
    output = OutputText(100)
    output.apply(
        update(
            ("old",),
            ((0, "C:>dir"), (1, "second")),
            replace_all=True,
            columns=80,
            row_count=2,
            cursor=(1, 3),
        )
    )
    assert output.terminal_cursor_index() == len("old\nC:>dir\nsec")


def test_the_column_stays_inside_the_row() -> None:
    output = OutputText(100)
    output.apply(update((), ((0, "C:>"),), replace_all=True, columns=80, cursor=(0, 4)))
    assert output.terminal_cursor_index() == len("C:>")  # the blank after '>' was stripped


def test_a_cursor_on_a_row_that_is_not_shown_is_at_the_end_of_the_text() -> None:
    output = OutputText(100, show_history=True)
    output.apply(
        update((), ((0, "prompt"),), replace_all=True, columns=80, row_count=24, cursor=(5, 0))
    )
    assert output.terminal_cursor_index() == len("prompt")
    output.set_show_history(False)  # every row is shown, the cursor row exists and is blank
    assert output.terminal_cursor_index() == len("prompt\n") + 4  # 4 blank rows before it


def test_the_cursor_of_a_line_program_is_at_the_end_of_the_unfinished_line() -> None:
    output = OutputText(100)
    output.apply(update(("done",), ((0, "50%"),), replace_all=True, cursor=(0, 3)))
    assert output.terminal_cursor_index() == len("done\n50%")


def test_the_live_part_starts_after_the_fixed_lines_and_ends_with_the_text() -> None:
    output = OutputText(100)
    output.apply(update(("one", "two"), ((0, "live"),), replace_all=True))
    assert output.live_start_index() == len("one\ntwo\n")
    assert output.live_end_index() == len("one\ntwo\nlive")


def test_without_fixed_lines_the_live_part_starts_at_the_beginning() -> None:
    output = OutputText(100)
    output.apply(update((), ((0, "live"),), replace_all=True))
    assert output.live_start_index() == 0


def test_clearing_forgets_the_cursor() -> None:
    output = OutputText(100)
    output.apply(update((), ((0, "text"),), replace_all=True, cursor=(0, 4)))
    output.clear()
    assert output.terminal_cursor_index() == 0


def test_the_width_is_that_of_the_terminal_screen_and_the_lines_of_the_application_keep_it() -> (
    None
):
    output = OutputText(100)
    assert output.columns == 0  # pipes: no width
    output.apply(update(rows=((0, "a"),), replace_all=True, columns=80, row_count=24))
    assert output.columns == 80
    output.apply(update(fixed=("# echoed by the application",)))  # columns 0
    assert output.columns == 80


# The closing part ------------------------------------------------------------------------------


def closing(*lines: str) -> ScreenUpdate:
    """An update that only sets the closing lines (``()`` empties them)."""
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


def test_the_closing_line_comes_after_the_live_part() -> None:
    output = OutputText(100)
    text = play(
        output,
        update(("fixed",), ((0, "screen one"), (1, "screen two")), replace_all=True, row_count=2),
        closing("Disconnected (code 255)."),
    )
    assert text == "fixed\nscreen one\nscreen two\nDisconnected (code 255)."


def test_the_live_part_ends_before_the_closing_part_and_the_text_ends_after_it() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    assert output.live_end_index() == len("screen")
    assert output.text[output.live_end_index() :] == "\nClosed."
    assert output.live_start_index() == 0
    assert output.has_closing


def test_the_cursor_past_the_live_rows_is_at_the_end_of_the_live_part_not_of_the_text() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "ab"),), replace_all=True, cursor=(3, 0)), closing("Closed."))
    assert output.terminal_cursor_index() == output.live_end_index()


def test_the_closing_part_is_one_change_from_the_end_of_the_live_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True))
    edit = output.apply(closing("Closed."))
    assert edit is not None
    assert (edit.start, edit.end, edit.replacement) == (6, 6, "\nClosed.")


def test_the_closing_part_and_a_last_change_of_the_live_part_make_one_change() -> None:
    output = OutputText(100)
    control = play(output, update(("a",), ((0, "old"),), replace_all=True))
    both = ScreenUpdate(
        fixed=(FixedLine("b"),),
        rows=(ScreenRow(0, "new"),),
        replace_all=False,
        overflows=(),
        columns=0,
        row_count=1,
        cursor_row=0,
        cursor_column=0,
        closing=(FixedLine("Closed."),),
    )
    edit = output.apply(both)
    assert edit is not None
    assert apply_edit(control, edit) == output.text == "a\nb\nnew\nClosed."


def test_the_closing_part_with_the_limit_of_the_output() -> None:
    output = OutputText(2)
    control = play(output, update(("a", "b", "c"), ((0, "x"),), replace_all=True))
    edit = output.apply(
        ScreenUpdate((FixedLine("d"),), (), False, (), 0, 1, 0, 0, (FixedLine("Closed."),))
    )
    assert edit is not None
    assert apply_edit(control, edit) == output.text == "c\nd\nx\nClosed."
    assert edit.trimmed_lines == 1


def test_an_update_that_says_nothing_of_it_keeps_the_closing_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    text = play(output, update((), ((0, "screen"),)))
    assert text == "screen\nClosed."


def test_the_next_output_empties_the_closing_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    text = play(output, update(("# SSH prod",)))  # the next connection writes its title
    assert text == "# SSH prod\nscreen"
    assert not output.has_closing


def test_a_new_screen_empties_the_closing_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    assert play(output, update((), ((0, "other"),), replace_all=True)) == "other"


def test_an_empty_closing_part_empties_it() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    assert play(output, closing()) == "screen"


def test_the_same_closing_part_again_changes_nothing() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    assert output.apply(closing("Closed.")) is None


def test_clearing_the_output_clears_the_closing_part() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "screen"),), replace_all=True), closing("Closed."))
    output.clear()
    assert (output.text, output.has_closing) == ("", False)


def test_the_caret_in_the_closing_part_stays_on_its_line_when_the_live_part_changes() -> None:
    output = OutputText(100)
    play(output, update((), ((0, "ab"),), replace_all=True), closing("Closed."))
    caret = len("ab\nClo")
    edit = output.apply(update((), ((0, "abcd"),)))
    assert edit is not None
    assert output.text[output.caret_after(caret, edit)] == "s"  # still in "Closed."
