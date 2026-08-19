"""Hide the title-bar close button on Windows (File > Exit is used instead)."""

from __future__ import annotations

import ctypes
import tkinter as tk

SC_CLOSE = 0xF060
MF_BYCOMMAND = 0x0000
MF_GRAYED = 0x0001


def disable_close_button(window: tk.Tk) -> None:
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        menu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        if not menu:
            return
        ctypes.windll.user32.DeleteMenu(menu, SC_CLOSE, MF_BYCOMMAND)
        ctypes.windll.user32.DrawMenuBar(hwnd)
    except Exception:
        # Alt+F4 / WM_DELETE_WINDOW is still intercepted by the app.
        pass
