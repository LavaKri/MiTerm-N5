"""Showing a context menu under a control, for the mouse and for the keyboard."""

import wx


def popup_context_menu(control: wx.Window, menu: wx.Menu, event: wx.ContextMenuEvent) -> None:
    """Show ``menu`` where the mouse is, or under the control when it comes from the keyboard
    (the Application key, Shift+F10: the event has no position)."""
    position = event.GetPosition()
    if position == wx.DefaultPosition:
        control.PopupMenu(menu, 0, control.GetSize().height)
    else:
        control.PopupMenu(menu, control.ScreenToClient(position))
