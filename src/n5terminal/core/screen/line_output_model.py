"""The output of a program run with pipes, as a screen model of one row.

Pipe mode follows the same model as the terminal modes (see "One model for every mode" in
``specs/interface.md``): the lines that are finished go to the fixed part, and the line being
written (a progress bar rewriting itself) is the live part, which has a single row. The presenter
then has one path for every transport.

Each stream (standard output, standard error) has its decoder and its output filter, and both write
in the same output, in arrival order. A line is never shared by the two streams: when the other
stream writes, the unfinished line is closed first. Each line of the standard error starts with
``STDERR_PREFIX``, once, whatever the rewrites of a progress bar.
"""

import threading

from n5terminal.core.screen.default_output_filter import DefaultOutputFilter
from n5terminal.core.screen.output_filter import FilteredChunk, FilterRules, OutputFilter
from n5terminal.core.screen.screen_model import FixedLine, ScreenRow, ScreenUpdate
from n5terminal.core.transport.stream_decoder import DEFAULT_FALLBACK, StreamDecoder
from n5terminal.core.transport.transport import Stream

# A longer line is cut (the rest goes on in the next line, marked continued). The default is an
# open question (``specs/open-questions.md``).
DEFAULT_MAX_LINE_LENGTH = 10_000
LF = "\n"
# Written at the start of each line of the standard error, so that it is told from the standard
# output by its text, not by position or colour. A technical name, like "Cmd": not translated.
STDERR_PREFIX = "StdErr: "


class _StreamState:
    def __init__(self, rules: FilterRules | None, fallback: str) -> None:
        self.decoder = StreamDecoder(fallback)
        self.filter: OutputFilter = DefaultOutputFilter(rules)


class LineOutputModel:
    """:class:`~n5terminal.core.screen.screen_model.ScreenModel` for programs run with pipes.

    Safe to call from the reader threads of the two streams. The size means nothing here: one row,
    no width (``columns`` is 0, there is no wrapping).
    """

    def __init__(
        self,
        rules: FilterRules | None = None,
        fallback: str = DEFAULT_FALLBACK,
        max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
        mark_stderr: bool = True,
    ) -> None:
        self._mark_stderr = mark_stderr
        self._lock = threading.Lock()
        self._streams = {stream: _StreamState(rules, fallback) for stream in Stream}
        self._max_line_length = max_line_length
        self._fixed: list[FixedLine] = []
        self._current = ""
        self._owner: Stream | None = None  # the stream that wrote the unfinished line
        self._shown: str | None = None  # the live line as last handed out

    @property
    def columns(self) -> int:
        return 0

    @property
    def row_count(self) -> int:
        return 1

    @property
    def application_cursor_keys(self) -> bool:
        return False

    def feed(self, data: bytes, stream: Stream = Stream.OUTPUT) -> None:
        """Give bytes of ``stream`` (by default the standard output)."""
        state = self._streams[stream]
        with self._lock:
            self._add(stream, state.filter.feed(state.decoder.decode(data)))

    def finish(self) -> None:
        """The streams ended: release what the decoders and filters hold back."""
        with self._lock:
            for stream, state in self._streams.items():
                text = state.decoder.finish()
                chunks = state.filter.feed(text) if text else []
                self._add(stream, [*chunks, *state.filter.finish()])

    def resize(self, columns: int, rows: int) -> None:
        """Nothing to do: pipes have no screen."""

    def take_update(self) -> ScreenUpdate:
        with self._lock:
            fixed = tuple(self._fixed)
            self._fixed = []
            changed = self._shown != self._current
            self._shown = self._current
            rows = (ScreenRow(0, self._current),) if changed else ()
            return ScreenUpdate(
                fixed=fixed,
                rows=rows,
                replace_all=changed,
                overflows=(),
                columns=0,
                row_count=1,
                cursor_row=0,
                cursor_column=len(self._current),
            )

    def _add(self, stream: Stream, chunks: list[FilteredChunk]) -> None:
        for chunk in chunks:
            if not chunk.text and not chunk.replaces_current_line:
                continue
            if self._current and self._owner is not stream:
                self._close_line()
            self._owner = stream
            if chunk.replaces_current_line:
                self._current = self._marked(stream, chunk.text)
                self._cut_long_line()
            else:
                self._append(stream, chunk.text)

    def _append(self, stream: Stream, text: str) -> None:
        *lines, last = text.split(LF)
        for line in lines:
            self._write(stream, line)
            self._close_line()
        self._write(stream, last)

    def _write(self, stream: Stream, text: str) -> None:
        """Add ``text`` to the line; a line of the standard error is marked where it starts."""
        self._current += text if self._current else self._marked(stream, text)
        self._cut_long_line()

    def _marked(self, stream: Stream, text: str) -> str:
        """``text`` with the mark of the standard error when it comes from it (not a blank one)."""
        if self._mark_stderr and stream is Stream.ERROR and text:
            return STDERR_PREFIX + text
        return text

    def _close_line(self) -> None:
        self._fixed.append(FixedLine(self._current))
        self._current = ""

    def _cut_long_line(self) -> None:
        limit = self._max_line_length
        while len(self._current) > limit:
            self._fixed.append(FixedLine(self._current[:limit], continued=True))
            self._current = self._current[limit:]
