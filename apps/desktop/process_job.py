"""Job Object Windows: fechar o handle encerra o worker e todos os descendentes."""
import ctypes
from ctypes import wintypes
import os


class Job:
    def __init__(self, process):
        if os.name != "nt":
            self.posix_group=process.pid
            if os.getpgid(process.pid)!=process.pid:
                process.kill(); process.wait(timeout=10)
                raise RuntimeError("Não foi possível criar o grupo isolado de processamento.")
            return
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Counters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        self.handle = kernel.CreateJobObjectW(None, None)
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000
        if not self.handle or not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            if self.handle:
                kernel.CloseHandle(self.handle)
            self.handle = None
            process.kill()
            process.wait(timeout=10)
            raise RuntimeError("Windows não permitiu iniciar o processo supervisionado.")

    def close(self):
        if os.name!="nt":
            import signal
            if self.posix_group:
                try: os.killpg(self.posix_group,signal.SIGKILL)
                except ProcessLookupError: pass
                self.posix_group=None
            return
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
