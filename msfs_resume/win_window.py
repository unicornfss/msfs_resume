"""Windows title-bar tweaks: hide Close, apply the app icon."""

from __future__ import annotations

import ctypes
import tkinter as tk
from pathlib import Path

SC_CLOSE = 0xF060
MF_BYCOMMAND = 0x0000
MF_GRAYED = 0x0001

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1


def _hwnd(window: tk.Misc) -> int:
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    return hwnd or int(window.winfo_id())


def disable_close_button(window: tk.Tk) -> None:
    try:
        hwnd = _hwnd(window)
        menu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        if not menu:
            return
        ctypes.windll.user32.DeleteMenu(menu, SC_CLOSE, MF_BYCOMMAND)
        ctypes.windll.user32.DrawMenuBar(hwnd)
    except Exception:
        # Alt+F4 / WM_DELETE_WINDOW is still intercepted by the app.
        pass


def apply_window_icon(window: tk.Tk, ico: Path) -> None:
    """Replace the Tk feather with the .ico in the title bar and on dialogs."""
    if not ico.exists():
        return
    path = str(ico.resolve())
    try:
        window.iconbitmap(path)
        window.iconbitmap(default=path)
    except tk.TclError:
        pass
    try:
        hwnd = _hwnd(window)
        load = ctypes.windll.user32.LoadImageW
        load.restype = ctypes.c_void_p
        small = load(None, path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        big = load(None, path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if small:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
        if big:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
    except Exception:
        pass
