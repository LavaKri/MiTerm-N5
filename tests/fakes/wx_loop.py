"""Run a real wx event loop until a condition holds (the window's timer ticks as in the app).

``wx.Yield`` is avoided for the slow tests: it dispatches messages from inside a call, where the
accessibility clients of the machine (a running screen reader) may call back into the window and
make COM refuse (``RPC_E_CANTCALLBACK_INCALL``). A loop that runs the way ``MainLoop`` does has not
that problem.
"""

import time
from collections.abc import Callable

import wx

POLL_MS = 20


def run_until(condition: Callable[[], bool], timeout: float = 15.0) -> bool:
    """Run the event loop until ``condition()`` is true; false when ``timeout`` seconds passed."""
    loop = wx.GUIEventLoop()
    activator = wx.EventLoopActivator(loop)
    deadline = time.monotonic() + timeout
    reached = [False]

    def poll() -> None:
        if condition():
            reached[0] = True
            loop.Exit()
        elif time.monotonic() >= deadline:
            loop.Exit()
        else:
            wx.CallLater(POLL_MS, poll)

    wx.CallAfter(poll)
    loop.Run()
    del activator
    return reached[0]
