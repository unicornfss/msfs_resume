"""Secondary windows: settings, about, changelog, error log, exit confirm."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from . import __version__
from .applog import LOG_PATH, email_error_log, read_log_tail
from .constants import APP_NAME, CONTACT_EMAIL, LICENSE_NAME
from .paths import bundled_file
from .settings import save_settings

BG = "#16181d"
PANEL = "#22262e"
PANEL_2 = "#2b303b"
TEXT = "#eef0f3"
MUTED = "#9aa3af"
GOLD = "#d4b45a"
FONT = "Segoe UI"


def _style_win(win: tk.Toplevel, title: str, size: str = "520x420") -> None:
    win.title(title)
    win.configure(bg=BG)
    win.geometry(size)
    win.transient(win.master)
    win.grab_set()


def open_settings(parent: tk.Tk, settings: dict, on_apply) -> None:
    win = tk.Toplevel(parent)
    _style_win(win, "Settings", "440x260")
    pad = tk.Frame(win, bg=PANEL)
    pad.pack(fill="both", expand=True, padx=16, pady=16)

    simbrief = tk.StringVar(value=str(settings.get("simbrief_username", "")))
    tol = tk.StringVar(value=str(settings.get("fuel_tolerance_pct", 5)))
    topmost = tk.BooleanVar(value=bool(settings.get("always_on_top")))

    tk.Label(pad, text="SimBrief username or ID", fg=MUTED, bg=PANEL, font=(FONT, 9)).pack(anchor="w")
    tk.Entry(pad, textvariable=simbrief, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", pady=(2, 10))
    tk.Label(pad, text="Fuel restore tolerance %", fg=MUTED, bg=PANEL, font=(FONT, 9)).pack(anchor="w")
    ttk.Spinbox(pad, from_=1, to=25, increment=1, textvariable=tol, width=8).pack(anchor="w", pady=(2, 10))
    tk.Checkbutton(
        pad, text="Always on top", variable=topmost, fg=TEXT, bg=PANEL,
        activebackground=PANEL, activeforeground=TEXT, selectcolor=PANEL_2,
        font=(FONT, 9), highlightthickness=0,
    ).pack(anchor="w", pady=(0, 14))

    def apply() -> None:
        try:
            settings["fuel_tolerance_pct"] = min(25.0, max(1.0, float(tol.get())))
        except ValueError:
            pass
        settings["simbrief_username"] = simbrief.get().strip()
        settings["always_on_top"] = bool(topmost.get())
        save_settings(settings)
        on_apply()
        win.destroy()

    tk.Button(pad, text="Save", command=apply, bg=GOLD, fg="#1a1408", font=(FONT, 10, "bold"), relief="flat", pady=6).pack(fill="x")


def open_text_window(parent: tk.Tk, title: str, text: str) -> None:
    win = tk.Toplevel(parent)
    _style_win(win, title, "640x480")
    box = tk.Text(win, wrap="word", bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", font=(FONT, 10))
    box.pack(fill="both", expand=True, padx=12, pady=12)
    box.insert("1.0", text)
    box.configure(state="disabled")


def _bundled_text(name: str, missing: str) -> str:
    path = bundled_file(name)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return missing


def open_help(parent: tk.Tk) -> None:
    open_text_window(
        parent,
        "How to use MSFS Resume",
        _bundled_text("HELP.md", "Help file was not found in this install."),
    )


def open_changelog(parent: tk.Tk) -> None:
    open_text_window(
        parent,
        "Changelog",
        _bundled_text("CHANGELOG.md", "Changelog file was not found in this install."),
    )


def open_error_log(parent: tk.Tk) -> None:
    win = tk.Toplevel(parent)
    _style_win(win, "Error log", "700x480")
    box = tk.Text(win, wrap="word", bg=PANEL, fg=TEXT, relief="flat", font=("Consolas", 9))
    box.pack(fill="both", expand=True, padx=12, pady=(12, 8))
    box.insert("1.0", read_log_tail(max_chars=20000))
    box.configure(state="disabled")
    btns = tk.Frame(win, bg=BG)
    btns.pack(fill="x", padx=12, pady=(0, 12))

    def open_folder() -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            LOG_PATH.write_text("", encoding="utf-8")
        os.startfile(LOG_PATH.parent)  # noqa: S606 — Windows Explorer

    tk.Button(btns, text="Open log folder", command=open_folder, bg=PANEL_2, fg=TEXT, relief="flat", padx=10, pady=6).pack(side="left")
    tk.Button(
        btns, text=f"Email to {CONTACT_EMAIL}", command=email_error_log,
        bg=GOLD, fg="#1a1408", relief="flat", padx=10, pady=6,
    ).pack(side="left", padx=8)


def open_about(parent: tk.Tk) -> None:
    licence = bundled_file("LICENSE.txt")
    licence_text = licence.read_text(encoding="utf-8") if licence.exists() else LICENSE_NAME
    text = (
        f"{APP_NAME}  v{__version__}\n\n"
        f"Contact: {CONTACT_EMAIL}\n\n"
        "Virtual airlines are welcome to get in touch about incorporating resume "
        "into their own flight-logging software. For freeware VAs that assistance "
        "is free of charge. No timescale or successful implementation is guaranteed.\n\n"
        f"{licence_text}"
    )
    open_text_window(parent, "About MSFS Resume", text)


def confirm_exit_while_recording(parent: tk.Tk) -> str:
    """Return 'cancel', 'minimise', or 'exit'."""
    win = tk.Toplevel(parent)
    _style_win(win, "Flight is recording", "460x220")
    result = {"value": "cancel"}
    pad = tk.Frame(win, bg=PANEL)
    pad.pack(fill="both", expand=True, padx=16, pady=16)
    tk.Label(
        pad, text="A flight is being recorded", fg=GOLD, bg=PANEL, font=(FONT, 12, "bold"),
    ).pack(anchor="w")
    tk.Label(
        pad,
        text="If you exit, recording stops until you open the app again. The last restore point is kept on disk. You can minimise to the tray instead and keep recording.",
        fg=TEXT, bg=PANEL, font=(FONT, 9), wraplength=410, justify="left",
    ).pack(anchor="w", pady=(8, 16))
    btns = tk.Frame(pad, bg=PANEL)
    btns.pack(fill="x")

    def choose(value: str) -> None:
        result["value"] = value
        win.destroy()

    tk.Button(btns, text="Cancel", command=lambda: choose("cancel"), bg=PANEL_2, fg=TEXT, relief="flat", padx=10, pady=7).pack(side="left")
    tk.Button(btns, text="Minimise", command=lambda: choose("minimise"), bg=PANEL_2, fg=TEXT, relief="flat", padx=10, pady=7).pack(side="left", padx=8)
    tk.Button(btns, text="Exit", command=lambda: choose("exit"), bg=GOLD, fg="#1a1408", relief="flat", padx=10, pady=7).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
    parent.wait_window(win)
    return result["value"]
