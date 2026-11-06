"""The UI Automation provider and the sink built on it.

What Windows does with a notification (a screen reader saying it) is heard by hand; here the
object is checked as UI Automation uses it: through its table of functions.
"""

import ctypes
from collections.abc import Iterator
from ctypes import byref, c_int, c_void_p

import pytest
import wx

from n5terminal.core.config.announcements import NullMessageSink
from n5terminal.ui.message_sinks import UiaMessageSink, create_sink
from n5terminal.ui.uia_provider import (
    CONTROL_TYPE_TEXT,
    E_NOINTERFACE,
    IID_SIMPLE,
    IID_UNKNOWN,
    PROPERTY_CONTROL_TYPE,
    PROPERTY_IS_CONTROL_ELEMENT,
    PROPERTY_NAME,
    PROVIDER_OPTIONS,
    S_OK,
    VARIANT_SIZE,
    UiaProvider,
)

pytestmark = pytest.mark.ui

QUERY = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
OPTIONS = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
PROPERTY = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_int, c_void_p)
HOST = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
SERVER_SIDE = 0x2


@pytest.fixture
def frame(app: wx.App) -> Iterator[wx.Frame]:
    window = wx.Frame(None)
    wx.Panel(window)
    yield window
    window.Destroy()


@pytest.fixture
def provider(frame: wx.Frame) -> Iterator[UiaProvider]:
    host = wx.Window(frame.GetChildren()[0], size=wx.Size(1, 1))
    result = UiaProvider(host.GetHandle())
    yield result
    result.disconnect()
    host.Destroy()


def method(provider: UiaProvider, index: int, prototype: type) -> object:
    return prototype(provider.table[index])


def test_the_provider_answers_for_unknown_and_for_itself(provider: UiaProvider) -> None:
    query = method(provider, 0, QUERY)
    for iid in (IID_UNKNOWN, IID_SIMPLE):
        buffer = ctypes.create_string_buffer(iid, 16)
        result = c_void_p()
        assert query(provider.address, ctypes.addressof(buffer), byref(result)) == S_OK  # type: ignore[operator]
        assert result.value == provider.address
    other = ctypes.create_string_buffer(b"\x01" * 16, 16)
    result = c_void_p(1)
    assert query(provider.address, ctypes.addressof(other), byref(result)) == E_NOINTERFACE  # type: ignore[operator]
    assert result.value is None


def test_the_provider_is_a_server_side_provider_on_our_thread(provider: UiaProvider) -> None:
    options = c_int()
    assert method(provider, 3, OPTIONS)(provider.address, byref(options)) == S_OK  # type: ignore[operator]
    assert options.value == PROVIDER_OPTIONS
    assert options.value & SERVER_SIDE


def read_property(provider: UiaProvider, property_id: int) -> tuple[int, int]:
    """The type and the first 8 bytes of the value of a property."""
    buffer = ctypes.create_string_buffer(VARIANT_SIZE)
    method(provider, 5, PROPERTY)(provider.address, property_id, buffer)  # type: ignore[operator]
    return ctypes.c_ushort.from_buffer(buffer).value, ctypes.c_longlong.from_buffer(buffer, 8).value


def test_the_element_is_a_text_control_element_named_after_the_last_text(
    provider: UiaProvider,
) -> None:
    assert read_property(provider, PROPERTY_CONTROL_TYPE) == (3, CONTROL_TYPE_TEXT)
    assert read_property(provider, PROPERTY_IS_CONTROL_ELEMENT) == (11, 0xFFFF)  # VARIANT_TRUE
    provider.name = "Program stopped."
    vt, pointer = read_property(provider, PROPERTY_NAME)
    assert vt == 8
    assert ctypes.wstring_at(pointer) == "Program stopped."


def test_an_unknown_property_is_left_to_the_window(provider: UiaProvider) -> None:
    assert read_property(provider, 99999) == (0, 0)


def test_the_provider_hands_over_to_the_window(provider: UiaProvider) -> None:
    host = c_void_p()
    assert method(provider, 6, HOST)(provider.address, byref(host)) == S_OK  # type: ignore[operator]
    assert host.value


def test_a_notification_is_raised_without_error(provider: UiaProvider) -> None:
    provider.raise_notification("Hello", "test")
    provider.raise_notification("Accents é and a very long text " * 50, "test")
    assert provider.name.startswith("Accents")


def test_disconnecting_twice_does_no_harm(provider: UiaProvider) -> None:
    provider.disconnect()
    provider.disconnect()


def test_the_uia_sink_is_made_for_the_uia_output(frame: wx.Frame) -> None:
    sink = create_sink("uia", frame)
    assert isinstance(sink, UiaMessageSink)
    sink.show("Hello")
    sink.close()


def test_no_output_makes_a_null_sink(frame: wx.Frame) -> None:
    assert isinstance(create_sink("none", frame), NullMessageSink)
