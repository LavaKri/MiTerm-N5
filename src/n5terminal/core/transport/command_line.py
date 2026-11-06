"""Split a typed command line into arguments, with the rules of Windows programs (C runtime).

``subprocess`` joins the arguments again with the same rules, so the program receives what the
user typed. Rules: spaces and tabs separate arguments outside quotes; ``2n`` backslashes before a
quote give ``n`` backslashes and the quote opens or closes; ``2n + 1`` backslashes before a quote
give ``n`` backslashes and a literal quote; other backslashes are literal; inside quotes, two
quotes give a literal quote.
"""

from dataclasses import dataclass, field

WHITESPACE = " \t"
QUOTE = '"'
BACKSLASH = "\\"


def split_command_line(line: str) -> tuple[str, ...]:
    """The arguments of ``line``; an empty tuple when it holds none."""
    return _Splitter().run(line)


@dataclass(slots=True)
class _Splitter:
    arguments: list[str] = field(default_factory=list)
    current: list[str] = field(default_factory=list)
    started: bool = False
    quoted: bool = False
    backslashes: int = 0

    def run(self, line: str) -> tuple[str, ...]:
        index = 0
        while index < len(line):
            index = self._step(line, index)
        self._end_argument()
        return tuple(self.arguments)

    def _step(self, line: str, index: int) -> int:
        char = line[index]
        if char == BACKSLASH:
            self.backslashes += 1
            self.started = True
            return index + 1
        if char == QUOTE:
            return self._quote(line, index)
        self._flush_backslashes()
        if char in WHITESPACE and not self.quoted:
            self._end_argument()
        else:
            self.current.append(char)
            self.started = True
        return index + 1

    def _quote(self, line: str, index: int) -> int:
        self.current.append(BACKSLASH * (self.backslashes // 2))
        escaped = self.backslashes % 2 == 1
        self.backslashes = 0
        self.started = True
        if escaped:
            self.current.append(QUOTE)
            return index + 1
        if self.quoted and line[index + 1 : index + 2] == QUOTE:
            self.current.append(QUOTE)
            return index + 2
        self.quoted = not self.quoted
        return index + 1

    def _flush_backslashes(self) -> None:
        self.current.append(BACKSLASH * self.backslashes)
        self.backslashes = 0

    def _end_argument(self) -> None:
        self._flush_backslashes()
        if self.started:
            self.arguments.append("".join(self.current))
        self.current = []
        self.started = False
