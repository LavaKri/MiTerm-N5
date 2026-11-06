"""The commands typed so far, to pick from a list."""

from collections import deque

from n5terminal.core.config.profiles import CommandUse

DEFAULT_LIMIT = 20  # per session, not a setting (specs/interface.md)


class CommandHistory:
    """Remembers the last commands with their use, the most recent last.

    A command typed with no program is a launch command; a line typed in a program that stays open
    (a shell) is a program command. ``BOTH`` is only for the commands of a profile.
    """

    def __init__(self, limit: int = DEFAULT_LIMIT) -> None:
        self._items: deque[tuple[str, CommandUse]] = deque(maxlen=limit)

    def add(self, command: str, use: CommandUse = CommandUse.LAUNCH) -> None:
        """Remember ``command`` as the most recent (a blank one is not kept).

        A command already there, of the same use, is not repeated: its older place is dropped.
        """
        if not command.strip():
            return
        kept = [item for item in self._items if item != (command, use)]
        self._items.clear()
        self._items.extend([*kept, (command, use)][-(self._items.maxlen or 0) :])

    def items(self) -> tuple[str, ...]:
        """All the commands, the most recent last."""
        return tuple(command for command, _use in self._items)

    def items_of(self, use: CommandUse) -> tuple[str, ...]:
        """The commands of that use, the most recent last."""
        return tuple(command for command, kind in self._items if kind is use)
