"""Small Win32 helpers through ctypes (no pywin32 dependency).

Every function is a safe no-op on non-Windows platforms so the rest of the
code (and the test-suite) runs everywhere.
"""
from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

VK_LBUTTON, VK_RBUTTON, VK_SHIFT, VK_CONTROL, VK_MENU, VK_ESCAPE = 0x01, 0x02, 0x10, 0x11, 0x12, 0x1B

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        dwmapi = ctypes.WinDLL("dwmapi")
    except OSError:  # pragma: no cover
        dwmapi = None

    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def key_down(vk: int) -> bool:
    if not IS_WINDOWS:
        return False
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def primary_button_vk() -> int:
    """Respects 'swap mouse buttons' (left-handed users)."""
    if IS_WINDOWS and user32.GetSystemMetrics(23):  # SM_SWAPBUTTON
        return VK_RBUTTON
    return VK_LBUTTON


def cursor_pos() -> tuple[int, int]:
    if not IS_WINDOWS:
        return 0, 0
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


_name_cache: dict[int, str] = {}


def _process_name(pid: int) -> str:
    if pid in _name_cache:
        return _name_cache[pid]
    name = ""
    h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                name = os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(h)
    if len(_name_cache) > 256:
        _name_cache.clear()
    _name_cache[pid] = name
    return name


def window_info_at_cursor() -> tuple[str, str]:
    """(process exe name, window class) of the top-level window under the cursor."""
    if not IS_WINDOWS:
        return "", ""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return "", ""
    root = user32.GetAncestor(hwnd, 2) or hwnd  # GA_ROOT
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(root, cls, 256)
    return _process_name(pid.value), cls.value


def set_dark_titlebar(hwnd: int, caption: str = "#08090D", text: str = "#D4AF37", border: str = "#3A3220") -> None:
    """Dark caption (Win10 1809+) and custom colours (Win11 22000+)."""
    if not IS_WINDOWS or dwmapi is None:
        return

    def colorref(hex_color: str) -> int:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r | (g << 8) | (b << 16)

    def set_attr(attr: int, value: int) -> bool:
        v = ctypes.c_int(value)
        return dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v)) == 0

    if not set_attr(20, 1):  # DWMWA_USE_IMMERSIVE_DARK_MODE
        set_attr(19, 1)      # older Windows 10 builds
    set_attr(35, colorref(caption))  # DWMWA_CAPTION_COLOR
    set_attr(36, colorref(text))     # DWMWA_TEXT_COLOR
    set_attr(34, colorref(border))   # DWMWA_BORDER_COLOR


def set_app_user_model_id(app_id: str) -> None:
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
    except Exception:  # noqa: BLE001
        pass


_mutex = None


def create_named_mutex(name: str) -> None:
    """Lets the installer/uninstaller detect a running Alfred (AppMutex)."""
    global _mutex
    if IS_WINDOWS and _mutex is None:
        _mutex = kernel32.CreateMutexW(None, False, name)


def allow_foreground_for_any() -> None:
    """Called by a secondary instance so the primary may take the foreground."""
    if IS_WINDOWS:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY


def force_foreground(hwnd: int) -> None:
    """Bring our window to the foreground despite the foreground lock."""
    if not IS_WINDOWS:
        return
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return
    cur = kernel32.GetCurrentThreadId()
    other = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = False
    try:
        if other and other != cur:
            attached = bool(user32.AttachThreadInput(other, cur, True))
        user32.SetForegroundWindow(wintypes.HWND(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(other, cur, False)
