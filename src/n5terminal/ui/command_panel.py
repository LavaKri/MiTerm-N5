"""The command field, its "Mask the message" box and its Send button, at the bottom of the window.

One field and one button; what they do depends on the state of the session (``InputMode``): a
command line to launch, or text sent to the running program. The label is created right before the
field, so that screen readers pair them, and it follows the state: "Commande", the program whose
arguments the field takes, or "Message" (rule of "Accessible interfaces" in
``specs/working-rules.md``). The presenter gives the words.

The box hides what is typed, for a secret the program asks for. It is only for text sent to a
running program (greyed when a command is typed), and it clears itself after each send, so that the
next command is not hidden by mistake.
"""

from collections.abc import Callable

import wx

from n5terminal.i18n import _
from n5terminal.presenters.session_view import InputMode
from n5terminal.ui.context_menu import popup_context_menu
from n5terminal.ui.hidden_text import hide_text


class CommandPanel(wx.Panel):
    """``on_submit(text, hidden)`` for Enter and the button.

    The context menu (History and the text commands) is given by the window, with
    ``set_context_menu``.

    Up and Down are not taken: they stay the keys of the text field.
    """

    def __init__(
        self,
        parent: wx.Window,
        on_submit: Callable[[str, bool], None],
    ) -> None:
        super().__init__(parent)
        self._on_submit = on_submit
        self._label = wx.StaticText(self, label=_("Command"))
        self.field = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER, name=_("Command"))
        # The order of creation is the order of Tab: the field, the box, the button.
        self.hide_box = wx.CheckBox(self, label=_("Mask the message"))
        self.hide_box.Disable()
        self.button = wx.Button(self, label=_("Send"))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        sizer.Add(self.field, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        sizer.Add(self.hide_box, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        sizer.Add(self.button, 0, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)
        self.field.Bind(wx.EVT_TEXT_ENTER, lambda _event: self._send())
        self.field.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._context_menu: wx.Menu | None = None
        self.button.Bind(wx.EVT_BUTTON, lambda _event: self._send())
        self.hide_box.Bind(wx.EVT_CHECKBOX, lambda _event: self._apply_hiding())

    def set_input_mode(self, mode: InputMode, label: str) -> None:
        """The label, and so the name of the field, follows what the field is for."""
        self._label.SetLabelText(label)  # as written: an & in a profile name is not a mnemonic
        self.field.SetName(label)
        if mode is InputMode.COMMAND:  # a command line is not a secret: nothing to hide
            self._set_hiding(False)
        self.hide_box.Enable(mode is InputMode.PROGRAM_INPUT)
        self.Layout()

    def clear(self) -> None:
        """Empty the field after a send; what was hidden is not hidden any more."""
        self.field.Clear()
        self._set_hiding(False)

    def show_text(self, text: str) -> None:
        """Put ``text`` in the field, the caret at its end."""
        self.field.SetValue(text)
        self.field.SetInsertionPointEnd()

    def set_context_menu(self, menu: wx.Menu) -> None:
        """The menu of the field (right click, Application key, Shift+F10)."""
        self._context_menu = menu

    def focus_field(self) -> None:
        self.field.SetFocus()

    def _send(self) -> None:
        self._on_submit(self.field.GetValue(), self.hide_box.GetValue())

    def _set_hiding(self, hidden: bool) -> None:
        self.hide_box.SetValue(hidden)
        self._apply_hiding()

    def _apply_hiding(self) -> None:
        hide_text(self.field, self.hide_box.GetValue())

    def _on_context_menu(self, event: wx.ContextMenuEvent) -> None:
        if self._context_menu is None:
            event.Skip()
            return
        popup_context_menu(self.field, self._context_menu, event)
