"""Stop a program together with the processes it started, through a Windows Job object.

While the program runs, the job kills its processes when it is closed, so that if MiTerm-N5 ends
or crashes, nothing it started keeps running unseen. Once the program has ended normally,
:meth:`keep_after_close` lifts that rule: a process it left on purpose (an editor opened by a
command, for example) goes on. :meth:`terminate`, asked by the user, stops the whole tree at any
time.
"""

import ctypes
import logging
import threading
from ctypes import wintypes
from typing import NoReturn

from n5terminal.core.errors import ProcessTreeError

logger = logging.getLogger(__name__)

PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
STOPPED_EXIT_CODE = 1
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    )


class _IoCounters(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    )


class _BasicAccountingInformation(ctypes.Structure):
    _fields_ = (
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    )


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.SetInformationJobObject.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
)
_kernel32.SetInformationJobObject.restype = wintypes.BOOL
_kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
_kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
_kernel32.TerminateJobObject.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.QueryInformationJobObject.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.LPVOID,
)
_kernel32.QueryInformationJobObject.restype = wintypes.BOOL


def _failure(action: str) -> ProcessTreeError:
    return ProcessTreeError(action, ctypes.get_last_error())


class ProcessTree:
    """The job holding one program and every process it starts afterwards."""

    def __init__(self, pid: int) -> None:
        self._lock = threading.Lock()  # the methods are called from different threads
        job = _kernel32.CreateJobObjectW(None, None)
        if not job:
            raise _failure("CreateJobObject")
        self._job: int | None = job
        if not self._set_kill_on_close(job, kill=True):
            self._abandon(_failure("SetInformationJobObject"))
        process = _kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not process:
            self._abandon(_failure("OpenProcess"))
        assigned = bool(_kernel32.AssignProcessToJobObject(job, process))
        failure = None if assigned else _failure("AssignProcessToJobObject")
        _kernel32.CloseHandle(process)
        if failure is not None:
            self._abandon(failure)

    def terminate(self) -> None:
        """Stop every process of the tree."""
        with self._lock:
            if self._job is not None and not _kernel32.TerminateJobObject(
                self._job, STOPPED_EXIT_CODE
            ):
                raise _failure("TerminateJobObject")

    def active_processes(self) -> int:
        """How many processes of the tree are alive: the program and everything it started."""
        with self._lock:
            if self._job is None:
                return 0
            information = _BasicAccountingInformation()
            if not _kernel32.QueryInformationJobObject(
                self._job,
                JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                ctypes.byref(information),
                ctypes.sizeof(information),
                None,
            ):
                raise _failure("QueryInformationJobObject")
            return int(information.ActiveProcesses)

    def keep_after_close(self) -> None:
        """The program ended normally: closing the job will no longer kill what is left."""
        with self._lock:
            if self._job is not None and not self._set_kill_on_close(self._job, kill=False):
                raise _failure("SetInformationJobObject")

    def close(self) -> None:
        """Release the job; it kills what is left unless :meth:`keep_after_close` was called."""
        with self._lock:
            if self._job is not None:
                _kernel32.CloseHandle(self._job)
                self._job = None

    def _abandon(self, failure: ProcessTreeError) -> NoReturn:
        self.close()
        raise failure

    @staticmethod
    def _set_kill_on_close(job: int, *, kill: bool) -> bool:
        information = _ExtendedLimitInformation()
        if kill:
            information.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        return bool(
            _kernel32.SetInformationJobObject(
                job,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(information),
                ctypes.sizeof(information),
            )
        )


def hold_process_tree(pid: int) -> ProcessTree | None:
    """The job of a program; ``None`` when Windows refuses it (then only the program stops)."""
    try:
        return ProcessTree(pid)
    except ProcessTreeError:
        logger.warning("No job for the program: its child processes cannot be stopped with it")
        return None


def keep_children(tree: ProcessTree | None) -> None:
    """The program ended normally: what it left running must survive MiTerm-N5."""
    if tree is None:
        return
    try:
        tree.keep_after_close()
    except ProcessTreeError:
        logger.warning("Cannot keep the child processes: they stop with MiTerm-N5")


def terminate_tree(tree: ProcessTree | None) -> bool:
    """Stop the whole tree; false without a job or when Windows refused (stop the program then)."""
    if tree is None:
        return False
    try:
        tree.terminate()
    except ProcessTreeError:
        logger.warning("Cannot stop the process tree, stopping the program only")
        return False
    return True
