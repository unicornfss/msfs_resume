from __future__ import annotations

import json
from pathlib import Path

from .fuel import DEFAULT_FLOOR_KG, DEFAULT_TOLERANCE_PCT

APP_DIR = Path.home() / "AppData" / "Roaming" / "MsfsResume"
SETTINGS_PATH = APP_DIR / "settings.json"
SNAPSHOT_PATH = APP_DIR / "last_snapshot.json"


def ensure_app_dir() -> Path:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DIR


def load_settings() -> dict:
    ensure_app_dir()
    defaults = {
        "fuel_tolerance_pct": DEFAULT_TOLERANCE_PCT,
        "fuel_floor_kg": DEFAULT_FLOOR_KG,
        "always_on_top": False,
        "simbrief_username": "",
        "start_in_tray": True,
        "show_tray_hint": True,
    }
    if not SETTINGS_PATH.exists():
        return defaults
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    defaults.update({k: data[k] for k in defaults if k in data})
    return defaults


def save_settings(settings: dict) -> None:
    ensure_app_dir()
    payload = {k: v for k, v in settings.items() if k != "github_repo"}
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
