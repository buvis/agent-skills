"""Windows process containment for the qwen evaluation harness: one job object.

Loaded only where `os.name == "nt"`, because `ctypes.WinDLL` exists nowhere
else. This repository declares no runtime dependencies, so kernel32 is reached
through `ctypes` rather than through `pywin32`, and every call below declares
its argtypes and restype: an undeclared pointer argument is truncated to 32 bits
on a 64-bit host, and the failure that follows looks like a random bad handle.
"""
import ctypes
from ctypes import wintypes

# `subprocess` exports CREATE_NEW_CONSOLE, CREATE_NEW_PROCESS_GROUP,
# CREATE_NO_WINDOW, DETACHED_PROCESS and the priority classes, and nothing else,
# so the flag that holds a child between creation and its first instruction has
# to be named here.
CREATE_SUSPENDED = 0x00000004

# The backstop: a harness that dies without reaping still takes the tree with
# it, because the job's last handle dies with the process holding it.
_KILL_ON_JOB_CLOSE = 0x00002000
_EXTENDED_LIMITS = 9
_PROCESS_ID_LIST = 3
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_TH32CS_SNAPTHREAD = 0x00000004
_THREAD_SUSPEND_RESUME = 0x0002
_ERROR_MORE_DATA = 234
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_RESUME_FAILED = 0xFFFFFFFF
_KILLED_RC = 1
# The pid list is read into a buffer of this many entries. A tree larger than it
# overflows the buffer and still answers "there are members", which is the only
# thing the reap asks of it.
_MAX_LISTED_PIDS = 1024


class Win32Error(RuntimeError):
    """A kernel32 call that failed, carrying which one and the code it left.

    The run-level halt is raised from this, so a job that could not be created
    and an assignment the host refused stay tellable apart in the record.
    """

    def __init__(self, call: str, code: int) -> None:
        super().__init__("%s failed: %d" % (call, code))
        self.call = call
        self.code = code


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    """Field for field as the headers have it: the limit flags live in here."""

    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    """Never read here, but it sits between the limits and the memory caps."""

    _fields_ = [
        ("ReadOperationCount", wintypes.ULARGE_INTEGER),
        ("WriteOperationCount", wintypes.ULARGE_INTEGER),
        ("OtherOperationCount", wintypes.ULARGE_INTEGER),
        ("ReadTransferCount", wintypes.ULARGE_INTEGER),
        ("WriteTransferCount", wintypes.ULARGE_INTEGER),
        ("OtherTransferCount", wintypes.ULARGE_INTEGER),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    """What the job is configured with; a field out of order is a flag out of place."""

    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class JOBOBJECT_BASIC_PROCESS_ID_LIST(ctypes.Structure):
    """The job's live members: the trailing array is declared with room to spare."""

    _fields_ = [
        ("NumberOfAssignedProcesses", wintypes.DWORD),
        ("NumberOfProcessIdsInList", wintypes.DWORD),
        ("ProcessIdList", ctypes.c_size_t * _MAX_LISTED_PIDS),
    ]


class THREADENTRY32(ctypes.Structure):
    """One snapshot row; the suspended child's thread is the one that names it owner."""

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int,
                                              wintypes.LPVOID, wintypes.DWORD)
_kernel32.SetInformationJobObject.restype = wintypes.BOOL
_kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
_kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
_kernel32.TerminateJobObject.restype = wintypes.BOOL
_kernel32.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int,
                                                wintypes.LPVOID, wintypes.DWORD,
                                                wintypes.LPDWORD)
_kernel32.QueryInformationJobObject.restype = wintypes.BOOL
_kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_kernel32.OpenThread.restype = wintypes.HANDLE
_kernel32.ResumeThread.argtypes = (wintypes.HANDLE,)
_kernel32.ResumeThread.restype = wintypes.DWORD
_kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.Thread32First.argtypes = (wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
_kernel32.Thread32First.restype = wintypes.BOOL
_kernel32.Thread32Next.argtypes = (wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
_kernel32.Thread32Next.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL


def create_job():
    """A job whose members die when its last handle closes, so none can be orphaned."""
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        raise Win32Error("CreateJobObjectW", ctypes.get_last_error())
    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    limits.BasicLimitInformation.LimitFlags |= _KILL_ON_JOB_CLOSE
    limited = _kernel32.SetInformationJobObject(
        job, _EXTENDED_LIMITS, ctypes.byref(limits), ctypes.sizeof(limits))
    if not limited:
        code = ctypes.get_last_error()
        _kernel32.CloseHandle(job)
        raise Win32Error("SetInformationJobObject", code)
    return job


def assign_process(job, pid: int) -> None:
    """Join a process to the job by pid: `subprocess` keeps its handle to itself.

    `AssignProcessToJobObject` requires both rights on the handle it is given,
    so quota and terminate are what the assignment itself needs, not rights the
    caller reserves for anything later.
    """
    access = _PROCESS_SET_QUOTA | _PROCESS_TERMINATE
    process = _kernel32.OpenProcess(access, False, pid)
    if not process:
        raise Win32Error("OpenProcess", ctypes.get_last_error())
    try:
        if not _kernel32.AssignProcessToJobObject(job, process):
            raise Win32Error("AssignProcessToJobObject", ctypes.get_last_error())
    finally:
        _kernel32.CloseHandle(process)


def terminate_job(job) -> None:
    """End every member at once, which reaches a grandchild whose parent has gone."""
    if not _kernel32.TerminateJobObject(job, _KILLED_RC):
        raise Win32Error("TerminateJobObject", ctypes.get_last_error())


def job_process_ids(job) -> list:
    """The pids still in the job: the whole of what the tree handle reads."""
    listing = JOBOBJECT_BASIC_PROCESS_ID_LIST()
    listed = _kernel32.QueryInformationJobObject(
        job, _PROCESS_ID_LIST, ctypes.byref(listing), ctypes.sizeof(listing), None)
    code = ctypes.get_last_error()
    # A tree that overflows the buffer fills it and reports ERROR_MORE_DATA. The
    # list comes back short, and "there are members left" is still the answer.
    if not listed and code != _ERROR_MORE_DATA:
        raise Win32Error("QueryInformationJobObject", code)
    return list(listing.ProcessIdList[:listing.NumberOfProcessIdsInList])


def close_job(job) -> None:
    """Let the job handle go: with no handle left, the job ends what it still holds."""
    if not _kernel32.CloseHandle(job):
        raise Win32Error("CloseHandle", ctypes.get_last_error())


def resume_process(pid: int) -> None:
    """Let a suspended child go: `Popen` hands back no handle to its initial thread.

    So the thread is found the long way round, by walking a snapshot for the
    threads that name this pid as their owner.
    """
    snapshot = _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
    if snapshot == _INVALID_HANDLE:
        raise Win32Error("CreateToolhelp32Snapshot", ctypes.get_last_error())
    entry = THREADENTRY32()
    entry.dwSize = ctypes.sizeof(THREADENTRY32)
    try:
        walking = _kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while walking:
            if entry.th32OwnerProcessID == pid:
                _resume_thread(entry.th32ThreadID)
            walking = _kernel32.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        _kernel32.CloseHandle(snapshot)


def _resume_thread(thread_id: int) -> None:
    """Resume one thread, saying so when the host refuses rather than walking on.

    A refusal here leaves the child suspended forever, which the bound would
    read as a hang and blame on the command.
    """
    thread = _kernel32.OpenThread(_THREAD_SUSPEND_RESUME, False, thread_id)
    if not thread:
        raise Win32Error("OpenThread", ctypes.get_last_error())
    try:
        if _kernel32.ResumeThread(thread) == _RESUME_FAILED:
            raise Win32Error("ResumeThread", ctypes.get_last_error())
    finally:
        _kernel32.CloseHandle(thread)
