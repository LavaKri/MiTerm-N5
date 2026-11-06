"""A fake of what the foreground guard asks of Windows: it records the calls it receives."""

from n5terminal.core.transport.foreground import Holder


class FakeForeground:
    """``take_back_results``: the answers to the calls of ``take_back``, then always True."""

    def __init__(
        self,
        holder: Holder = Holder.OTHER,
        *,
        lock_allowed: bool = True,
        take_back_results: tuple[bool, ...] = (),
    ) -> None:
        self.current = holder
        self.lock_allowed = lock_allowed
        self.take_back_results = list(take_back_results)
        self.calls: list[str] = []

    def holder(self) -> Holder:
        return self.current

    def lock(self) -> bool:
        self.calls.append("lock")
        return self.lock_allowed

    def unlock(self) -> bool:
        self.calls.append("unlock")
        return True

    def take_back(self, window: int) -> bool:
        self.calls.append(f"take_back {window}")
        succeeded = self.take_back_results.pop(0) if self.take_back_results else True
        if succeeded:
            self.current = Holder.OWN_WINDOW  # the main window holds the foreground again
        return succeeded

    def describe_foreground(self) -> str:
        return "a fake window"
