"""A minimal UI Automation provider for one window, written with ``ctypes`` (Windows only).

A screen reader that listens to UI Automation says the *notification events* raised on an element.
The procedure Windows documents for a custom control hosted in a window: the window answers
``WM_GETOBJECT`` with its provider (``UiaReturnRawElementProvider``) and the provider implements
``IRawElementProviderSimple``, hosted in that same window. Navigation, identity and bounds come
from the host window, so no fragment interface is needed. No MSAA, no API of one screen reader.
"""

import ctypes
import os
import sys
import uuid
from collections.abc import Callable
from ctypes import c_int, c_long, c_short, c_size_t, c_ssize_t, c_ulong, c_ushort, c_void_p

import wx

from n5terminal.core.errors import ScreenReaderOutputError

# ProviderOptions_ServerSideProvider | ProviderOptions_UseComThreading (calls come on our thread)
PROVIDER_OPTIONS = 0x2 | 0x20
WM_GETOBJECT = 0x003D
UIA_ROOT_OBJECT_ID = -25
S_OK = 0
E_NOINTERFACE = c_long(0x80004002).value

IID_UNKNOWN = uuid.UUID("00000000-0000-0000-C000-000000000046").bytes_le
IID_SIMPLE = uuid.UUID("D6DD68D1-86FD-4332-8666-9ABEDEA2D24C").bytes_le

VT_I4 = 3
VT_BSTR = 8
VT_BOOL = 11
PROPERTY_PROCESS_ID = 30002
PROPERTY_CONTROL_TYPE = 30003
PROPERTY_NAME = 30005
PROPERTY_IS_ENABLED = 30010
PROPERTY_IS_CONTROL_ELEMENT = 30016
PROPERTY_IS_CONTENT_ELEMENT = 30017
PROPERTY_NATIVE_WINDOW_HANDLE = 30020
CONTROL_TYPE_TEXT = 50020
TRUE_PROPERTIES = (PROPERTY_IS_ENABLED, PROPERTY_IS_CONTROL_ELEMENT, PROPERTY_IS_CONTENT_ELEMENT)
VARIANT_SIZE = 24  # bytes on 64 bits

# UiaRaiseNotificationEvent: kind "other", processing "important, most recent only".
NOTIFICATION_KIND_OTHER = 4
PROCESSING_IMPORTANT_MOST_RECENT = 1

HRESULT = c_long

#: Every provider created. UI Automation may still call a provider after its window is gone (it
#: lets go of its references later), so a provider and its callbacks are never freed.
_PROVIDERS: list[UiaProvider] = []


def _store(address: int | None, value: int) -> None:
    """Write the pointer-sized ``value`` at ``address`` (an output parameter), if there is one."""
    if address:
        c_void_p.from_address(address).value = value


class UiaProvider:
    """The provider of the window ``hwnd``: a text element whose name is the last text said.

    It hooks the window procedure to give itself to UI Automation; :meth:`disconnect` undoes that
    when the window is destroyed.
    """

    def __init__(self, hwnd: int) -> None:
        if sys.platform != "win32":
            raise ScreenReaderOutputError("UI Automation exists only on Windows.")
        self.hwnd = hwnd
        self.name = ""
        try:
            self._uia = ctypes.WinDLL("UIAutomationCore.dll")
            self._ole = ctypes.WinDLL("oleaut32.dll")
            self._comctl = ctypes.WinDLL("comctl32.dll")
        except OSError as error:
            raise ScreenReaderOutputError(str(error)) from error
        self._declare_functions()
        function = ctypes.WINFUNCTYPE
        methods: tuple[tuple[type, Callable[..., int]], ...] = (
            (function(HRESULT, c_void_p, c_void_p, c_void_p), self._query_interface),
            (function(c_ulong, c_void_p), self._add_ref),
            (function(c_ulong, c_void_p), self._release),
            (function(HRESULT, c_void_p, c_void_p), self._provider_options),
            (function(HRESULT, c_void_p, c_int, c_void_p), self._pattern_provider),
            (function(HRESULT, c_void_p, c_int, c_void_p), self._property_value),
            (function(HRESULT, c_void_p, c_void_p), self._host_provider),
        )
        self._callbacks = tuple(prototype(method) for prototype, method in methods)
        self.table = (c_void_p * len(methods))(
            *(ctypes.cast(callback, c_void_p) for callback in self._callbacks)
        )
        self._object = c_void_p(ctypes.addressof(self.table))
        #: The ``IRawElementProviderSimple`` pointer: the address of an object that starts with
        #: the address of its table of methods.
        self.address = ctypes.addressof(self._object)
        self._subclass = function(
            c_ssize_t, c_void_p, ctypes.c_uint, c_size_t, c_ssize_t, c_size_t, c_size_t
        )(self._window_proc)
        if not self._comctl.SetWindowSubclass(hwnd, self._subclass, 1, 0):
            raise ScreenReaderOutputError("The window could not be hooked for UI Automation.")
        self._connected = True
        _PROVIDERS.append(self)

    def disconnect(self) -> None:
        """Unhook the window and tell UI Automation to let go of this provider (idempotent).

        To be called when the window is destroyed, as Microsoft documents for providers.
        """
        if not self._connected:
            return
        self._connected = False
        self._comctl.RemoveWindowSubclass(self.hwnd, self._subclass, 1)
        # Not now: this runs while the window is being destroyed, and a COM call made from
        # inside a window message is refused. Once the message is over it goes through.
        wx.CallAfter(self._uia.UiaDisconnectProvider, self.address)

    def _declare_functions(self) -> None:
        self._ole.SysAllocString.restype = c_void_p
        self._ole.SysAllocString.argtypes = [ctypes.c_wchar_p]
        self._ole.SysFreeString.restype = None
        self._ole.SysFreeString.argtypes = [c_void_p]
        self._comctl.DefSubclassProc.restype = c_ssize_t
        self._comctl.DefSubclassProc.argtypes = [c_void_p, ctypes.c_uint, c_size_t, c_ssize_t]
        self._comctl.RemoveWindowSubclass.restype = c_int
        self._comctl.RemoveWindowSubclass.argtypes = [c_void_p, c_void_p, c_size_t]
        self._uia.UiaReturnRawElementProvider.restype = c_ssize_t
        self._uia.UiaReturnRawElementProvider.argtypes = [c_void_p, c_size_t, c_ssize_t, c_void_p]
        self._uia.UiaDisconnectProvider.restype = HRESULT
        self._uia.UiaDisconnectProvider.argtypes = [c_void_p]
        self._uia.UiaHostProviderFromHwnd.restype = HRESULT
        self._uia.UiaHostProviderFromHwnd.argtypes = [c_void_p, ctypes.POINTER(c_void_p)]
        self._uia.UiaRaiseNotificationEvent.restype = HRESULT
        self._uia.UiaRaiseNotificationEvent.argtypes = [
            c_void_p,
            c_int,
            c_int,
            c_void_p,
            c_void_p,
        ]

    def raise_notification(self, text: str, activity: str) -> None:
        """Make the screen reader say ``text``, which also becomes the name of the element."""
        self.name = text
        text_bstr = self._ole.SysAllocString(text)
        activity_bstr = self._ole.SysAllocString(activity)
        try:
            result = self._uia.UiaRaiseNotificationEvent(
                self.address,
                NOTIFICATION_KIND_OTHER,
                PROCESSING_IMPORTANT_MOST_RECENT,
                text_bstr,
                activity_bstr,
            )
        finally:
            for bstr in (text_bstr, activity_bstr):
                if bstr:
                    self._ole.SysFreeString(bstr)
        if result < 0:
            code = result & 0xFFFFFFFF
            raise ScreenReaderOutputError(f"UiaRaiseNotificationEvent failed (0x{code:08X}).")

    def _window_proc(
        self, hwnd: int, message: int, wparam: int, lparam: int, subclass_id: int, data: int
    ) -> int:
        if message == WM_GETOBJECT and c_int(lparam).value == UIA_ROOT_OBJECT_ID:
            return int(self._uia.UiaReturnRawElementProvider(hwnd, wparam, lparam, self.address))
        return int(self._comctl.DefSubclassProc(hwnd, message, wparam, lparam))

    # IUnknown (the object lives as long as the process, so references are not counted)

    def _query_interface(self, this: int, riid: int, out: int | None) -> int:
        found = ctypes.string_at(riid, 16) in (IID_UNKNOWN, IID_SIMPLE)
        _store(out, self.address if found else 0)
        return S_OK if found else E_NOINTERFACE

    def _add_ref(self, this: int) -> int:
        return 2

    def _release(self, this: int) -> int:
        return 1

    # IRawElementProviderSimple

    def _provider_options(self, this: int, out: int | None) -> int:
        if out:
            c_int.from_address(out).value = PROVIDER_OPTIONS
        return S_OK

    def _pattern_provider(self, this: int, pattern_id: int, out: int | None) -> int:
        _store(out, 0)
        return S_OK

    def _property_value(self, this: int, property_id: int, out: int | None) -> int:
        if not out:
            return S_OK
        ctypes.memset(out, 0, VARIANT_SIZE)  # VT_EMPTY: the host window gives the rest
        if property_id == PROPERTY_NATIVE_WINDOW_HANDLE:
            self._set_variant(out, VT_I4, c_long, self.hwnd)
        elif property_id == PROPERTY_PROCESS_ID:
            self._set_variant(out, VT_I4, c_long, os.getpid())
        elif property_id == PROPERTY_CONTROL_TYPE:
            self._set_variant(out, VT_I4, c_long, CONTROL_TYPE_TEXT)
        elif property_id in TRUE_PROPERTIES:
            self._set_variant(out, VT_BOOL, c_short, -1)
        elif property_id == PROPERTY_NAME:
            self._set_variant(out, VT_BSTR, c_void_p, self._ole.SysAllocString(self.name))
        return S_OK

    @staticmethod
    def _set_variant(
        address: int, vt: int, value_type: type[c_long] | type[c_short] | type[c_void_p], value: int
    ) -> None:
        c_ushort.from_address(address).value = vt
        value_type.from_address(address + 8).value = value

    def _host_provider(self, this: int, out: int | None) -> int:
        provider = c_void_p()
        result = int(self._uia.UiaHostProviderFromHwnd(self.hwnd, ctypes.byref(provider)))
        _store(out, provider.value or 0)
        return result
