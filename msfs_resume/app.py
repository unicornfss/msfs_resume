"""Desktop UI for MSFS Resume."""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser
from datetime import datetime, timezone

from . import __version__
from .airports import Airport, load_cache, min_runway_ft, nearest_suitable, refresh_cache
from .applog import log_exception, logger, setup_logging
from .constants import CONTACT_EMAIL
from .dialogs import (
    DownloadProgress,
    confirm_exit_while_recording,
    open_about,
    open_changelog,
    open_error_log,
    open_help,
    open_settings,
)
from .flight_state import COMPLETE, INTERRUPT, INTERRUPTED, RECORDING, RESUME, TAKEOFF, WAITING, FlightTracker
from .fuel import fuel_band, in_band, kg_to_lb, lb_to_kg
from .settings import load_settings, save_settings
from .simbrief import SimBriefError, fetch_latest_ofp
from .simconnect_client import SimConnectClient
from .snapshot import FlightSnapshot, clear_snapshot, load_snapshot, save_snapshot
from .paths import bundled_file
from .tray import TrayIcon
from .updates import check_for_updates, download_installer, installer_dest
from .win_window import apply_window_icon, disable_close_button

BG = "#16181d"
PANEL = "#22262e"
PANEL_2 = "#2b303b"
TEXT = "#eef0f3"
MUTED = "#9aa3af"
GOLD = "#d4b45a"
GOOD = "#3dd68c"
BAD = "#f07178"
LINE = "#3a4050"
FONT = "Segoe UI"


def _fmt_kg(value: float) -> str:
    return f"{value:,.0f} kg"


def _fmt_lb(value: float) -> str:
    return f"{value:,.0f} lb"


def _fmt_hdg(value: float) -> str:
    return f"{int(round(value)) % 360:03d}°"


def _fmt_ias(value: float) -> str:
    return f"{value:.0f} kt"


def _fmt_alt(value: float) -> str:
    if value >= 10000:
        return f"FL{int(round(value / 100)):03d}  ({value:,.0f} ft)"
    return f"{value:,.0f} ft"


def _fmt_ll(lat: float, lon: float) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{abs(lat):.4f}°{ns}   {abs(lon):.4f}°{ew}"


def _age(iso: str) -> str:
    try:
        saved = datetime.fromisoformat(iso)
        if saved.tzinfo is None:
            saved = saved.replace(tzinfo=timezone.utc)
        seconds = max(0, int((datetime.now(timezone.utc) - saved).total_seconds()))
    except ValueError:
        return iso
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    hours, rem = divmod(seconds, 3600)
    return f"{hours}h {rem // 60:02d}m ago"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MSFS Resume")
        self.geometry("660x780")
        self.minsize(580, 640)
        self.configure(bg=BG)
        self.settings = load_settings()
        self.client = SimConnectClient()
        self.saved: FlightSnapshot | None = load_snapshot()
        self.ofp: dict | None = None
        self._airports: list[Airport] = load_cache()
        self._airports_error = False
        self._restoring = False
        self._resume_intent = False
        self._mode = "choose" if self.saved else "wait"
        self.tracker = FlightTracker(INTERRUPTED if self.saved else WAITING)
        self._status = tk.StringVar(value="Starting…")
        self._message = tk.StringVar(value="")
        self._tray = TrayIcon(
            on_show=lambda: self.after(0, self._restore_from_tray),
            on_exit=lambda: self.after(0, self._request_exit),
        )
        self._simbrief = tk.StringVar(value=str(self.settings.get("simbrief_username", "")))
        self._tol = tk.StringVar(value=str(self.settings.get("fuel_tolerance_pct", 5)))
        self._topmost = tk.BooleanVar(value=bool(self.settings.get("always_on_top")))
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._request_exit)
        self.bind("<Unmap>", self._on_unmap)
        self.attributes("-topmost", bool(self.settings.get("always_on_top")))
        self.after(400, self._apply_chrome)
        self.client.start()
        self.after(200, self._show_mode)
        self.after(400, self._tick)
        self.after(2500, lambda: self._check_updates(True))
        threading.Thread(target=self._load_airports, daemon=True).start()

    def _apply_chrome(self) -> None:
        apply_window_icon(self, bundled_file("assets", "msfs-resume.ico"))
        disable_close_button(self)

    def _build(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Settings...", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._request_exit)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to use", command=lambda: open_help(self))
        help_menu.add_command(label="Changelog", command=lambda: open_changelog(self))
        help_menu.add_command(label="Error log", command=lambda: open_error_log(self))
        help_menu.add_command(label="Check for updates", command=lambda: self._check_updates(False))
        help_menu.add_separator()
        help_menu.add_command(label="Contact", command=lambda: webbrowser.open(f"mailto:{CONTACT_EMAIL}"))
        help_menu.add_command(label="About", command=lambda: open_about(self))
        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(header, text="MSFS Resume", fg=TEXT, bg=BG, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(header, textvariable=self._status, fg=MUTED, bg=BG, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))

        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill="both", expand=True, padx=16)

        self._choose = self._panel()
        tk.Label(
            self._choose, text="Incomplete flight found", fg=GOLD, bg=PANEL,
            font=(FONT, 13, "bold"),
        ).pack(anchor="w")
        self._choose_summary = tk.Label(
            self._choose, text="", fg=TEXT, bg=PANEL, font=(FONT, 10),
            justify="left", wraplength=580, anchor="w",
        )
        self._choose_summary.pack(fill="x", pady=(8, 12))
        tk.Label(
            self._choose,
            text="Resume that flight, or start a new one. If you take off without choosing, it is treated as a new flight.",
            fg=MUTED, bg=PANEL, font=(FONT, 9), wraplength=580, justify="left", anchor="w",
        ).pack(fill="x")
        btns = tk.Frame(self._choose, bg=PANEL)
        btns.pack(fill="x", pady=(16, 0))
        tk.Button(
            btns, text="Resume flight", command=self._choose_resume,
            bg=GOLD, fg="#1a1408", font=(FONT, 11, "bold"), relief="flat", padx=12, pady=8, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            btns, text="Start new flight", command=self._choose_new,
            bg=PANEL_2, fg=TEXT, font=(FONT, 11, "bold"), relief="flat", padx=12, pady=8, cursor="hand2",
        ).pack(side="left", padx=(10, 0))

        self._wait = self._panel()
        tk.Label(self._wait, text="Waiting for takeoff", fg=GOLD, bg=PANEL, font=(FONT, 13, "bold")).pack(anchor="w")
        tk.Label(
            self._wait,
            text="Recording starts when the aircraft leaves the ground and ends when you are parked with engines off.",
            fg=MUTED, bg=PANEL, font=(FONT, 9), wraplength=580, justify="left", anchor="w",
        ).pack(fill="x", pady=(8, 0))

        self._record = self._panel()
        tk.Label(self._record, text="Flight recording", fg=GOOD, bg=PANEL, font=(FONT, 13, "bold")).pack(anchor="w")
        self._record_meta = tk.Label(
            self._record, text="", fg=MUTED, bg=PANEL, font=(FONT, 9), wraplength=580, justify="left", anchor="w",
        )
        self._record_meta.pack(fill="x", pady=(4, 10))
        self._record_rows: dict[str, tk.Label] = {}
        for key, label in (
            ("fuel", "Fuel"),
            ("alt", "Altitude"),
            ("heading", "Heading"),
            ("ias", "Airspeed"),
            ("pos", "Position"),
        ):
            row = tk.Frame(self._record, bg=PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, fg=MUTED, bg=PANEL, font=(FONT, 10), width=12, anchor="w").pack(side="left")
            value = tk.Label(row, text="—", fg=TEXT, bg=PANEL, font=(FONT, 11, "bold"), anchor="w")
            value.pack(side="left", fill="x", expand=True)
            self._record_rows[key] = value

        self._restore = self._panel()
        tk.Label(self._restore, text="Set these before restore", fg=GOLD, bg=PANEL, font=(FONT, 13, "bold")).pack(anchor="w")
        self._restore_meta = tk.Label(
            self._restore, text="", fg=MUTED, bg=PANEL, font=(FONT, 9),
            wraplength=580, justify="left", anchor="w",
        )
        self._restore_meta.pack(fill="x", pady=(4, 10))
        self._restore_rows: dict[str, tk.Label] = {}
        for key, label in (
            ("plan", "Flight"),
            ("route", "Route"),
            ("nearest", "Spawn near"),
            ("fuel", "Fuel on board"),
            ("range", "Allowed range"),
            ("current", "Current fuel"),
            ("heading", "Heading"),
            ("ias", "Airspeed"),
            ("alt", "Altitude"),
        ):
            row = tk.Frame(self._restore, bg=PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, fg=MUTED, bg=PANEL, font=(FONT, 9), width=14, anchor="nw").pack(side="left")
            value = tk.Label(row, text="—", fg=TEXT, bg=PANEL, font=(FONT, 10, "bold"), anchor="w", justify="left", wraplength=430)
            value.pack(side="left", fill="x", expand=True)
            self._restore_rows[key] = value
        self._gate = tk.Label(self._restore, text="", fg=MUTED, bg=PANEL, font=(FONT, 10, "bold"), anchor="w", wraplength=580, justify="left")
        self._gate.pack(fill="x", pady=(10, 8))
        self._restore_btn = tk.Button(
            self._restore, text="Restore flight", command=self._restore_now,
            bg=GOLD, fg="#1a1408", font=(FONT, 12, "bold"), relief="flat", padx=16, pady=10, cursor="hand2",
        )
        self._restore_btn.pack(fill="x")
        tk.Button(
            self._restore, text="Cancel — start a new flight instead", command=self._choose_new,
            bg=PANEL_2, fg=TEXT, font=(FONT, 9), relief="flat", pady=6, cursor="hand2",
        ).pack(fill="x", pady=(8, 0))

        tk.Label(self, textvariable=self._message, fg=MUTED, bg=BG, font=(FONT, 9), wraplength=620, justify="left").pack(
            fill="x", padx=16, pady=(6, 12),
        )

    def _panel(self) -> tk.Frame:
        frame = tk.Frame(self._body, bg=PANEL)
        inner_pad = tk.Frame(frame, bg=PANEL)
        inner_pad.pack(fill="both", expand=True, padx=16, pady=14)
        return inner_pad

    def _show_mode(self) -> None:
        for frame in (self._choose.master, self._wait.master, self._record.master, self._restore.master):
            frame.pack_forget()
        target = {
            "choose": self._choose.master,
            "wait": self._wait.master,
            "record": self._record.master,
            "restore": self._restore.master,
        }[self._mode]
        target.pack(fill="both", expand=True, pady=(0, 8))
        self._refresh()

    def _open_settings(self) -> None:
        def apply() -> None:
            self._simbrief.set(str(self.settings.get("simbrief_username", "")))
            self._tol.set(str(self.settings.get("fuel_tolerance_pct", 5)))
            self._topmost.set(bool(self.settings.get("always_on_top")))
            self.attributes("-topmost", bool(self.settings.get("always_on_top")))

        open_settings(self, self.settings, apply)

    def _check_updates(self, silent: bool) -> None:
        def worker() -> None:
            try:
                info = check_for_updates()
            except Exception as exc:
                log_exception("Update check failed", exc)
                if not silent:
                    self.after(0, lambda: messagebox.showerror("Updates", str(exc)))
                return

            def notify() -> None:
                if info.available:
                    if not messagebox.askyesno(
                        "Update available",
                        f"MSFS Resume {info.latest} is available (you have {info.current}).\n\n"
                        "Download and install it now?",
                    ):
                        return
                    if not info.installer_url:
                        messagebox.showerror(
                            "Updates",
                            "An update is available but no installer was attached to it.",
                        )
                        return
                    self._download_update(info)
                elif not silent:
                    messagebox.showinfo(
                        "Updates",
                        f"You are on {info.current}. No newer version was found.",
                    )

            self.after(0, notify)

        threading.Thread(target=worker, daemon=True).start()

    def _download_update(self, info) -> None:
        dest = installer_dest(info.installer_name or f"MSFSResumeSetup-{info.latest}.exe")
        dialog = DownloadProgress(self, dest.name)

        def worker() -> None:
            error = None
            try:
                download_installer(
                    info.installer_url,
                    dest,
                    progress=lambda got, total: self.after(0, dialog.set_progress, got, total),
                    should_cancel=lambda: dialog.cancelled,
                )
            except Exception as exc:
                error = exc
                if "cancelled" not in str(exc).lower():
                    log_exception("Update download failed", exc)

            def done() -> None:
                dialog.close()
                if dialog.cancelled:
                    return
                if error:
                    messagebox.showerror("Updates", f"Could not download the installer.\n\n{error}")
                    return
                if messagebox.askyesno(
                    "Install update",
                    f"The installer has been saved to:\n{dest}\n\n"
                    "MSFS Resume will close so the files can be replaced. Install now?",
                ):
                    self._run_installer(dest)

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _run_installer(self, dest) -> None:
        recording = self._mode == "record" and self.tracker.phase == RECORDING
        if recording:
            choice = confirm_exit_while_recording(self)
            if choice != "exit":
                if choice == "minimise":
                    self.iconify()
                messagebox.showinfo("Updates", f"The installer is still at:\n{dest}")
                return
        try:
            subprocess.Popen([str(dest)], close_fds=True)
        except OSError as exc:
            log_exception("Could not start installer", exc)
            messagebox.showerror(
                "Updates",
                f"Could not start the installer.\n\n{exc}\n\nFile:\n{dest}",
            )
            return
        self._force_exit()

    def _save_tol(self) -> None:
        try:
            value = float(self._tol.get())
        except ValueError:
            return
        self.settings["fuel_tolerance_pct"] = min(25.0, max(1.0, value))
        save_settings(self.settings)

    def _save_simbrief(self) -> None:
        self.settings["simbrief_username"] = self._simbrief.get().strip()
        save_settings(self.settings)

    def _toggle_topmost(self) -> None:
        self.settings["always_on_top"] = bool(self._topmost.get())
        save_settings(self.settings)
        self.attributes("-topmost", self._topmost.get())

    def _load_airports(self) -> None:
        try:
            if not self._airports:
                self._airports = refresh_cache()
        except Exception as exc:
            self._airports_error = True
            log_exception("Failed to download airport list", exc)
            return

    def _resume_setup_active(self) -> bool:
        """True while the user is preparing a restore. Takeoff must not start a new flight."""
        return self._resume_intent or self._mode == "restore"

    def _tick(self) -> None:
        with self.client.lock:
            live = self.client.live
            in_world = live.in_world
            on_ground = live.on_ground
            engines = live.engines_running
        if not self._restoring:
            if self._resume_setup_active():
                if in_world and not on_ground:
                    self._message.set(
                        "Saved restore point is held. Configure flaps, gear and lights, then click Restore flight."
                    )
            else:
                update = self.tracker.update(
                    in_world=in_world, on_ground=on_ground, engines_running=engines,
                )
                if update.event == TAKEOFF:
                    self._on_takeoff(new_flight=True)
                elif update.event == RESUME:
                    self._on_takeoff(new_flight=True)
                elif update.event == INTERRUPT:
                    self._message.set("Flight interrupted. Restore is kept until you finish or start a new flight.")
                    if self._mode == "record":
                        self._mode = "choose"
                        self._resume_intent = False
                        self.after(0, self._show_mode)
                elif update.event == COMPLETE:
                    self._finish_flight("Flight complete — parked with engines off. Waiting for the next takeoff.")
        if self.tracker.phase == RECORDING and not self._resume_setup_active():
            snap = self._live_snapshot()
            if snap is not None:
                self.saved = snap
                try:
                    save_snapshot(snap)
                except OSError as exc:
                    log_exception("Could not write snapshot file", exc)
        self._refresh()
        self.after(400, self._tick)

    def _live_snapshot(self) -> FlightSnapshot | None:
        snap = self.client.snapshot_if_ready()
        if snap is None:
            return None
        source = self.ofp or (self.saved.to_json() if self.saved else None)
        snap.apply_ofp(source)
        return snap

    def _on_takeoff(self, new_flight: bool) -> None:
        if new_flight and self.saved and self._mode in {"choose", "restore", "wait"}:
            clear_snapshot()
            self.saved = None
            self.ofp = None
        self._resume_intent = False
        self.tracker.reset(RECORDING)
        self._mode = "record"
        self._message.set("Takeoff detected — recording.")
        self._show_mode()
        if new_flight:
            threading.Thread(target=self._fetch_ofp, daemon=True).start()

    def _fetch_ofp(self) -> None:
        ident = self._simbrief.get().strip()
        if not ident:
            self.after(0, lambda: self._message.set("Recording. Add a SimBrief username to attach route details on takeoff."))
            return
        try:
            ofp = fetch_latest_ofp(ident)
        except SimBriefError as exc:
            log_exception("SimBrief fetch failed", exc)
            self.after(0, lambda: self._message.set(f"Recording. SimBrief: {exc}"))
            return
        self.ofp = ofp
        if self.saved:
            self.saved.apply_ofp(ofp)
            try:
                save_snapshot(self.saved)
            except OSError as exc:
                log_exception("Could not write snapshot after SimBrief fetch", exc)
        summary = f"{ofp.get('flight_number') or 'OFP'}  {ofp.get('origin_icao')} → {ofp.get('dest_icao')}".strip()
        self.after(0, lambda: self._message.set(f"Recording. SimBrief: {summary}"))

    def _finish_flight(self, message: str) -> None:
        self.saved = None
        self.ofp = None
        self._resume_intent = False
        clear_snapshot()
        self.tracker.reset(WAITING)
        self._mode = "wait"
        self._message.set(message)
        self._show_mode()

    def _choose_resume(self) -> None:
        if self.saved is None:
            return
        self._resume_intent = True
        self._mode = "restore"
        self._message.set(
            "Load near the suggested airport, set fuel, then configure the aircraft. "
            "Taking off to get gear and flaps sorted will not start a new flight."
        )
        self._show_mode()

    def _choose_new(self) -> None:
        self._finish_flight("Previous flight cleared. Recording starts at the next takeoff.")

    def _band(self, snapshot: FlightSnapshot) -> tuple[float, float]:
        try:
            pct = float(self._tol.get())
        except ValueError:
            pct = 5.0
        return fuel_band(
            snapshot.fuel_kg,
            tolerance_pct=pct,
            floor_kg=float(self.settings.get("fuel_floor_kg", 100)),
            capacity_kg=snapshot.capacity_kg,
        )

    def _nearest_text(self, snapshot: FlightSnapshot) -> str:
        aircraft = snapshot.aircraft_icao or snapshot.aircraft
        needed = min_runway_ft(aircraft)
        if not self._airports:
            if getattr(self, "_airports_error", False):
                return "Could not download the airport list. Spawn as close as you can to the last position."
            return f"Airport list still loading… spawn as close as you can to the last position. Need ~{needed:,} ft runway."
        matches = nearest_suitable(snapshot.latitude, snapshot.longitude, aircraft, self._airports, limit=3)
        if not matches:
            return f"No matching airport found nearby. Need about {needed:,} ft of runway."
        lines = []
        for airport, distance in matches:
            extra = "  (suggested spawn)" if not lines else ""
            lines.append(
                f"{airport.icao}  {distance:.0f} nm  ·  {airport.name}  ·  {airport.longest_ft:,.0f} ft{extra}"
            )
        return (
            "Spawn at the closest airport below on the world map, then restore. "
            "That keeps scenery streaming short.\n" + "\n".join(lines)
        )

    def _refresh(self) -> None:
        with self.client.lock:
            live = self.client.live
            connected = live.connected
            status = live.status
            current_fuel_kg = lb_to_kg(live.fuel_lb)
            aircraft = live.aircraft
            engines = live.engines_running
            in_world = live.in_world
            lat, lon = live.latitude, live.longitude
            heading = live.heading_mag
            ias = live.ias_kt
            alt = live.altitude_ft
            fuel_lb = live.fuel_lb

        self._status.set(status)
        if self._tray.visible:
            tip = "MSFS Resume"
            if self._mode == "record":
                tip = "MSFS Resume — recording"
            elif self._mode == "choose":
                tip = "MSFS Resume — incomplete flight"
            elif self._mode == "restore":
                tip = "MSFS Resume — ready to restore"
            self._tray.set_tooltip(tip)
        snapshot = self.saved

        if self._mode == "choose":
            if snapshot is None:
                self._mode = "wait"
                self._show_mode()
                return
            bits = [snapshot.aircraft or "Saved aircraft", _age(snapshot.saved_at)]
            if snapshot.flight_number or snapshot.origin_icao:
                bits.append(
                    f"{snapshot.flight_number}  {snapshot.origin_icao} → {snapshot.dest_icao}".strip()
                )
            bits.append(f"{_fmt_alt(snapshot.altitude_ft)}  ·  heading {_fmt_hdg(snapshot.heading_mag)}  ·  {_fmt_ias(snapshot.ias_kt)} IAS")
            self._choose_summary.config(text="\n".join(bits))
            return

        if self._mode == "record":
            fuel_text = _fmt_kg(current_fuel_kg) if connected else "—"
            if connected:
                fuel_text += f"   ({_fmt_lb(fuel_lb)})"
            self._record_rows["fuel"].config(text=fuel_text)
            self._record_rows["alt"].config(text=_fmt_alt(alt) if connected else "—")
            self._record_rows["heading"].config(text=_fmt_hdg(heading) if connected else "—")
            self._record_rows["ias"].config(text=f"{_fmt_ias(ias)} IAS" if connected else "—")
            self._record_rows["pos"].config(text=_fmt_ll(lat, lon) if connected and in_world else "Waiting for sim…")
            plan = ""
            if snapshot and snapshot.has_ofp:
                plan = f"{snapshot.flight_number}  {snapshot.origin_icao} → {snapshot.dest_icao}".strip()
            elif self.ofp:
                plan = f"{self.ofp.get('flight_number')}  {self.ofp.get('origin_icao')} → {self.ofp.get('dest_icao')}".strip()
            self._record_meta.config(text=plan or "Live restore point — SimBrief details attach on takeoff if a username is set.")
            return

        if self._mode != "restore" or snapshot is None:
            return

        plan = "No SimBrief plan stored for this flight."
        if snapshot.has_ofp:
            plan = (
                f"{snapshot.flight_number or snapshot.aircraft_icao or snapshot.aircraft}  "
                f"{snapshot.origin_icao} ({snapshot.origin_name}) → {snapshot.dest_icao} ({snapshot.dest_name})"
            ).strip()
        self._restore_rows["plan"].config(text=plan)
        self._restore_rows["route"].config(text=snapshot.route or "—")
        self._restore_rows["nearest"].config(text=self._nearest_text(snapshot))
        low, high = self._band(snapshot)
        self._restore_rows["fuel"].config(text=f"{_fmt_kg(snapshot.fuel_kg)}   ({_fmt_lb(snapshot.fuel_lb)})")
        self._restore_rows["range"].config(text=f"{_fmt_kg(low)}  –  {_fmt_kg(high)}")
        self._restore_rows["heading"].config(text=_fmt_hdg(snapshot.heading_mag))
        self._restore_rows["ias"].config(text=f"{_fmt_ias(snapshot.ias_kt)} IAS")
        self._restore_rows["alt"].config(text=_fmt_alt(snapshot.altitude_ft))
        self._restore_meta.config(
            text=f"{snapshot.aircraft}  ·  saved {_age(snapshot.saved_at)}. "
            "Set fuel first. Taking off to set heading, flaps, gear and lights will not start a new flight. "
            "FMC/MCDU is not restored — re-enter the route if needed."
        )

        fuel_ok = False
        if connected and in_world:
            fuel_ok = in_band(current_fuel_kg, low, high)
            self._restore_rows["current"].config(
                text=f"{_fmt_kg(current_fuel_kg)}   ({_fmt_lb(kg_to_lb(current_fuel_kg))})",
                fg=GOOD if fuel_ok else BAD,
            )
        else:
            self._restore_rows["current"].config(text="Waiting for sim…", fg=MUTED)

        airborne_ok = snapshot.on_ground or engines
        can_restore = connected and in_world and fuel_ok and airborne_ok and not self._restoring
        if can_restore:
            self._gate.config(text="Fuel in range — restore is available", fg=GOOD)
            self._restore_btn.config(state="normal", bg=GOLD, fg="#1a1408")
        elif not connected:
            self._gate.config(text="Connect to MSFS and load the aircraft before restoring", fg=MUTED)
            self._restore_btn.config(state="disabled", bg=LINE, fg=MUTED)
        elif not fuel_ok:
            self._gate.config(
                text=f"Set fuel to {_fmt_kg(snapshot.fuel_kg)}  (allowed {_fmt_kg(low)} – {_fmt_kg(high)})",
                fg=BAD,
            )
            self._restore_btn.config(state="disabled", bg=LINE, fg=MUTED)
        elif not airborne_ok:
            self._gate.config(text="Start the engines before restoring an airborne snapshot", fg=BAD)
            self._restore_btn.config(state="disabled", bg=LINE, fg=MUTED)
        else:
            self._gate.config(text="Restore unavailable", fg=MUTED)
            self._restore_btn.config(state="disabled", bg=LINE, fg=MUTED)

    def _restore_now(self) -> None:
        snapshot = self.saved
        if snapshot is None:
            return
        low, high = self._band(snapshot)
        with self.client.lock:
            current = lb_to_kg(self.client.live.fuel_lb)
        if not in_band(current, low, high):
            messagebox.showwarning(
                "Fuel out of range",
                f"Set fuel to {_fmt_kg(snapshot.fuel_kg)}.\nAllowed: {_fmt_kg(low)} – {_fmt_kg(high)}.",
            )
            return
        self._restoring = True
        self._restore_btn.config(state="disabled")
        self._message.set("Pausing and warping to the saved position…")

        def worker() -> None:
            error = None
            try:
                self.client.restore(snapshot)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                log_exception("Restore failed", exc)

            def done() -> None:
                self._restoring = False
                if error:
                    self._message.set(f"Restore failed: {error}")
                    messagebox.showerror(
                        "Restore failed",
                        f"{error}\n\nThis has been written to the error log.\n"
                        f"Help → Error log to review or email {CONTACT_EMAIL}.",
                    )
                else:
                    self._resume_intent = False
                    self.tracker.reset(RECORDING)
                    self._mode = "record"
                    self._message.set(
                        f"Restored  ·  {_fmt_hdg(snapshot.heading_mag)}  ·  "
                        f"{_fmt_ias(snapshot.ias_kt)} IAS  ·  {_fmt_alt(snapshot.altitude_ft)}"
                    )
                    self._show_mode()
                self._refresh()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_unmap(self, event) -> None:
        if event.widget is not self:
            return
        try:
            if self.state() == "iconic":
                self.after(0, self._minimize_to_tray)
        except tk.TclError:
            return

    def _minimize_to_tray(self) -> None:
        try:
            if self.state() != "iconic" and self.state() != "withdrawn":
                return
        except tk.TclError:
            return
        self.withdraw()
        tip = "MSFS Resume — recording" if self._mode == "record" else "MSFS Resume"
        self._tray.show(tip)

    def _restore_from_tray(self) -> None:
        self._tray.hide()
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _request_exit(self) -> None:
        try:
            if self.state() == "withdrawn":
                self._restore_from_tray()
        except tk.TclError:
            pass
        recording = self._mode == "record" and self.tracker.phase == RECORDING
        if recording:
            choice = confirm_exit_while_recording(self)
            if choice == "cancel":
                return
            if choice == "minimise":
                self.iconify()
                return
        self._force_exit()

    def _force_exit(self) -> None:
        self._save_simbrief()
        self._save_tol()
        self._tray.hide()
        self.client.stop()
        self.destroy()

    def _on_close(self) -> None:
        self._request_exit()


def main() -> None:
    setup_logging()
    logger.info("MSFS Resume %s starting", __version__)
    app = App()
    app.mainloop()
