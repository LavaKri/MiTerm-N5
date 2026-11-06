"""Where the announcements really go: the sinks of the outputs in ``core/config/screen_reader``."""

import wx

from n5terminal.core.config.announcements import MessageSink, NullMessageSink
from n5terminal.core.config.location import APP_NAME
from n5terminal.core.config.screen_reader import UIA

_ACTIVITY_ID = "n5terminal.announcement"


class _Announcer(wx.Window):
    """A one-pixel window, out of sight and never focused, that hosts the UI Automation provider."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, pos=wx.Point(-5, -5), size=wx.Size(1, 1), name=APP_NAME)

    def AcceptsFocus(self) -> bool:  # noqa: N802 (wx API)
        """Never takes the focus."""
        return False

    def AcceptsFocusFromKeyboard(self) -> bool:  # noqa: N802 (wx API)
        """Never reached with the Tab key."""
        return False


class UiaMessageSink:
    """Sends the messages as UI Automation notifications raised by a hidden window.

    The window is not a child of the status bar: screen readers read the children of the status
    bar with it and would add the name of this element (the last announcement) to what the status
    bar says. It is a child of the panel of the window (a second child of the frame itself would
    stop the panel from filling it). Nothing is shown on screen and no control takes the focus.
    Needs Windows 10 version 1709.
    """

    def __init__(self, window: wx.Frame) -> None:
        # Imported here: the module needs the Windows API, other platforms never reach this class.
        from n5terminal.ui.uia_provider import UiaProvider  # noqa: PLC0415

        panel = next((child for child in window.GetChildren() if isinstance(child, wx.Panel)), None)
        self._announcer = _Announcer(panel or window)
        self._provider = UiaProvider(self._announcer.GetHandle())
        self._announcer.Bind(wx.EVT_WINDOW_DESTROY, self._on_announcer_destroyed)

    def show(self, text: str) -> None:
        """Raise a notification carrying ``text`` (an empty text is not worth saying)."""
        if text.strip():
            self._provider.raise_notification(text, _ACTIVITY_ID)

    def _on_announcer_destroyed(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self._announcer:  # not the destruction of a child
            self._provider.disconnect()
        event.Skip()

    def close(self) -> None:
        """Remove the hidden window (when another output replaces this one)."""
        self._announcer.Destroy()


def create_sink(output_id: str, window: wx.Frame) -> MessageSink:
    """The sink of the output ``output_id``; ``ScreenReaderOutputError`` if it cannot be made."""
    if output_id == UIA.id:
        return UiaMessageSink(window)
    return NullMessageSink()
