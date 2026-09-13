"""Launch only the executable explicitly chosen in settings; do not stop the driver."""
import os
from pathlib import Path
import subprocess
import threading
import time

_processes = {}


def launch_osu(folder, server="bancho", gatari=True):
    path = (Path(folder).expanduser()/'osu!.exe').resolve()
    if not path.is_file(): raise ValueError('osu!.exe не найден / osu!.exe not found')
    key=(path,server if gatari else "bancho")
    previous = _processes.get(key)
    if previous is not None and previous.poll() is None: return previous
    args=[str(path)]+(["-devserver","osugatari.ru"] if server=="gatari" and gatari else [])
    process = subprocess.Popen(args,cwd=str(path.parent))
    _processes[key] = process
    return process


def launch_driver(value):
    path = Path(value).expanduser().resolve()
    if not value or path.suffix.lower() != '.exe' or not path.is_file():
        raise ValueError('Укажите существующий .exe драйвера планшета / Select a tablet driver executable')
    previous = _processes.get(path)
    if previous is not None and previous.poll() is None: return previous
    options = {}
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        options['startupinfo'] = startup
    process = subprocess.Popen([str(path)], cwd=str(path.parent), **options)
    _processes[path] = process
    if os.name == 'nt':
        threading.Thread(target=_minimize, args=(process,), daemon=True).start()
    return process


def _minimize(process):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.IsWindowVisible.argtypes = (wintypes.HWND,)
    user32.ShowWindowAsync.argtypes = (wintypes.HWND, ctypes.c_int)
    seen = set()
    @callback_type
    def visit(hwnd, unused):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and hwnd not in seen and user32.IsWindowVisible(hwnd):
            user32.ShowWindowAsync(hwnd, 7)
            seen.add(hwnd)
        return True
    for _ in range(40):
        if process.poll() is not None: break
        user32.EnumWindows(visit, 0)
        time.sleep(.25)
