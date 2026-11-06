"""A clipboard for the tests: no test reads or writes the clipboard of the computer.

It stands for ``wx.TheClipboard`` (``monkeypatch.setattr(wx, "TheClipboard", FakeClipboard())``).
It keeps every text it is given, so that a test can tell what was copied and in which order.
``available=False`` plays a clipboard that another program holds: ``Open`` fails. ``accepts=False``
plays one that opens but does not take the data: ``SetData`` fails.
"""

import wx


class FakeClipboard:
    def __init__(self, available: bool = True, accepts: bool = True) -> None:
        self.available = available
        self.accepts = accepts
        self.copied: list[str] = []  # every text set, the oldest first
        self.opened = False

    def Open(self) -> bool:  # noqa: N802 (wx API)
        self.opened = self.available
        return self.available

    def SetData(self, data: wx.TextDataObject) -> bool:  # noqa: N802 (wx API)
        assert self.opened, "the clipboard must be open to be written"
        if not self.accepts:
            return False
        self.copied.append(data.GetText())
        return True

    def Close(self) -> None:  # noqa: N802 (wx API)
        self.opened = False
