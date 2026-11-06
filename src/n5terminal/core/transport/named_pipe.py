"""The server end of a Windows named pipe that only the current user can open.

The askpass program that ``ssh`` runs (``specs/architecture/connection.md``, "The askpass program")
talks to the application through such a pipe, and what it carries is a password. So the pipe:

- is open to the current user alone, by its security descriptor (``D:P(A;;GA;;;<SID of the user>)``:
  not even the administrators), and refuses clients that come through the network;
- is created with ``FILE_FLAG_FIRST_PIPE_INSTANCE``, which fails when something else already holds
  the name, so that nothing can stand in for it;
- always has an instance, from the first one to the close: a new one is created as soon as a client
  is connected, so the name is never free for someone else to take.

One instance serves one client: :class:`PipeInstance` connects, then the connection reads a line and
writes a line, like a file.
"""

import ctypes
import msvcrt
import os
from ctypes import wintypes
from typing import BinaryIO

from n5terminal.core.errors import NamedPipeError

PIPE_PREFIX = "\\\\.\\pipe\\"
MAX_LINE = 64 * 1024  # a request is a short line of JSON: more than this is not one

_PIPE_ACCESS_DUPLEX = 0x00000003
_FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
_PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
_PIPE_UNLIMITED_INSTANCES = 255
_BUFFER_SIZE = 4096
_ERROR_PIPE_CONNECTED = 535  # the client came between the creation and the wait: it is connected
_TOKEN_QUERY = 0x0008
_TOKEN_USER = 1
_SDDL_REVISION_1 = 1
_INVALID_HANDLE = wintypes.HANDLE(-1).value


class _SecurityAttributes(ctypes.Structure):
    _fields_ = (
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    )


class _SidAndAttributes(ctypes.Structure):
    _fields_ = (("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD))


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
_kernel32.CreateNamedPipeW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(_SecurityAttributes),
)
_kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
_kernel32.ConnectNamedPipe.argtypes = (wintypes.HANDLE, wintypes.LPVOID)
_kernel32.ConnectNamedPipe.restype = wintypes.BOOL
_kernel32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
_kernel32.FlushFileBuffers.restype = wintypes.BOOL
_kernel32.CancelIoEx.argtypes = (wintypes.HANDLE, wintypes.LPVOID)
_kernel32.CancelIoEx.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.GetCurrentProcess.restype = wintypes.HANDLE
_kernel32.LocalFree.argtypes = (wintypes.LPVOID,)
_kernel32.LocalFree.restype = wintypes.LPVOID
_advapi32.OpenProcessToken.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
)
_advapi32.OpenProcessToken.restype = wintypes.BOOL
_advapi32.GetTokenInformation.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
)
_advapi32.GetTokenInformation.restype = wintypes.BOOL
_advapi32.ConvertSidToStringSidW.argtypes = (wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR))
_advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
_advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.LPVOID),
    wintypes.LPVOID,
)
_advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL


def _failure(action: str) -> NamedPipeError:
    return NamedPipeError(action, ctypes.get_last_error())


def current_user_sid() -> str:
    """The SID of the user this process runs as, as a string (``S-1-5-21-…``)."""
    token = wintypes.HANDLE()
    if not _advapi32.OpenProcessToken(_kernel32.GetCurrentProcess(), _TOKEN_QUERY, token):
        raise _failure("OpenProcessToken")
    try:
        size = wintypes.DWORD()
        _advapi32.GetTokenInformation(token, _TOKEN_USER, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not _advapi32.GetTokenInformation(
            token, _TOKEN_USER, buffer, size.value, ctypes.byref(size)
        ):
            raise _failure("GetTokenInformation")
        user = ctypes.cast(buffer, ctypes.POINTER(_SidAndAttributes)).contents
        text = wintypes.LPWSTR()
        if not _advapi32.ConvertSidToStringSidW(user.Sid, ctypes.byref(text)):
            raise _failure("ConvertSidToStringSid")
        try:
            return str(text.value)
        finally:
            _kernel32.LocalFree(ctypes.cast(text, wintypes.LPVOID))
    finally:
        _kernel32.CloseHandle(token)


def security_descriptor_text(sid: str) -> str:
    """The descriptor (SDDL) that gives every right to ``sid`` and to nobody else."""
    return f"D:P(A;;GA;;;{sid})"


class PipeConnection:
    """A connected client: a binary file to read a line from and to write a line to."""

    def __init__(self, handle: int) -> None:
        self._handle = handle
        fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        self._file: BinaryIO = os.fdopen(fd, "r+b", buffering=0)

    def readline(self) -> bytes:
        """A line of at most ``MAX_LINE`` bytes, with its line break; empty when the client left."""
        return self._file.readline(MAX_LINE)

    def write(self, data: bytes) -> None:
        self._file.write(data)

    def cancel(self) -> None:
        """Stop a read that waits for a client that never writes (the pipe is being closed)."""
        _kernel32.CancelIoEx(self._handle, None)

    def close(self) -> None:
        """Let the client read what was written, then close."""
        try:
            _kernel32.FlushFileBuffers(self._handle)  # waits until the client has read it
        finally:
            self._file.close()


class PipeInstance:
    """One instance of the pipe, waiting for a client."""

    def __init__(self, name: str, first: bool, security_descriptor: str) -> None:
        if not name.startswith(PIPE_PREFIX):
            raise NamedPipeError("name", 0)
        descriptor = wintypes.LPVOID()
        if not _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            security_descriptor, _SDDL_REVISION_1, ctypes.byref(descriptor), None
        ):
            raise _failure("ConvertStringSecurityDescriptor")
        try:
            attributes = _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), descriptor, False)
            opening = _PIPE_ACCESS_DUPLEX | (_FILE_FLAG_FIRST_PIPE_INSTANCE if first else 0)
            handle = _kernel32.CreateNamedPipeW(
                name,
                opening,
                _PIPE_REJECT_REMOTE_CLIENTS,  # byte stream, blocking
                _PIPE_UNLIMITED_INSTANCES,
                _BUFFER_SIZE,
                _BUFFER_SIZE,
                0,
                ctypes.byref(attributes),
            )
            error = ctypes.get_last_error()
        finally:
            _kernel32.LocalFree(descriptor)
        if handle in (None, _INVALID_HANDLE):
            raise NamedPipeError("CreateNamedPipe", error)
        self._handle: int | None = handle

    def wait_for_client(self) -> PipeConnection:
        """Block until a client connects; the instance becomes the connection."""
        handle = self._handle
        if handle is None:
            raise NamedPipeError("closed", 0)
        connected = _kernel32.ConnectNamedPipe(handle, None)
        error = ctypes.get_last_error()
        if not connected and error != _ERROR_PIPE_CONNECTED:
            raise NamedPipeError("ConnectNamedPipe", error)
        self._handle = None
        return PipeConnection(handle)

    def close(self) -> None:
        """Close an instance nobody connected to."""
        handle, self._handle = self._handle, None
        if handle is not None:
            _kernel32.CloseHandle(handle)
