from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

from .settings import SNAPSHOT_PATH, ensure_app_dir


@dataclass
class FlightSnapshot:
    saved_at: str
    aircraft: str
    latitude: float
    longitude: float
    altitude_ft: float
    heading_mag: float
    heading_true: float
    ias_kt: float
    tas_kt: float
    vertical_speed_fpm: float
    pitch_deg: float
    bank_deg: float
    on_ground: bool
    fuel_lb: float
    fuel_gal: float
    fuel_capacity_gal: float
    fuel_lb_per_gal: float
    engines_running: bool
    autopilot: bool
    origin_icao: str = ""
    origin_name: str = ""
    dest_icao: str = ""
    dest_name: str = ""
    route: str = ""
    flight_number: str = ""
    aircraft_icao: str = ""

    @property
    def fuel_kg(self) -> float:
        from .fuel import lb_to_kg

        return lb_to_kg(self.fuel_lb)

    @property
    def capacity_kg(self) -> float | None:
        from .fuel import lb_to_kg

        if self.fuel_capacity_gal <= 0 or self.fuel_lb_per_gal <= 0:
            return None
        return lb_to_kg(self.fuel_capacity_gal * self.fuel_lb_per_gal)

    @property
    def has_ofp(self) -> bool:
        return bool(self.origin_icao or self.dest_icao or self.route)

    def apply_ofp(self, ofp: dict | None) -> None:
        if not ofp:
            return
        self.origin_icao = ofp.get("origin_icao", "") or self.origin_icao
        self.origin_name = ofp.get("origin_name", "") or self.origin_name
        self.dest_icao = ofp.get("dest_icao", "") or self.dest_icao
        self.dest_name = ofp.get("dest_name", "") or self.dest_name
        self.route = ofp.get("route", "") or self.route
        self.flight_number = ofp.get("flight_number", "") or self.flight_number
        self.aircraft_icao = ofp.get("aircraft_icao", "") or self.aircraft_icao

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> FlightSnapshot:
        from dataclasses import MISSING

        kwargs = {}
        for field in fields(cls):
            if field.name in data:
                kwargs[field.name] = data[field.name]
            elif field.default is not MISSING:
                kwargs[field.name] = field.default
            elif field.default_factory is not MISSING:
                kwargs[field.name] = field.default_factory()
            else:
                raise KeyError(field.name)
        return cls(**kwargs)


def save_snapshot(snapshot: FlightSnapshot, path: Path | None = None) -> None:
    ensure_app_dir()
    target = path or SNAPSHOT_PATH
    target.write_text(json.dumps(snapshot.to_json(), indent=2), encoding="utf-8")


def load_snapshot(path: Path | None = None) -> FlightSnapshot | None:
    target = path or SNAPSHOT_PATH
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return FlightSnapshot.from_json(data)
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return None


def clear_snapshot(path: Path | None = None) -> None:
    target = path or SNAPSHOT_PATH
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
