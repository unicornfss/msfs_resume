"""Estimate the next SimBrief waypoint from a recorded position."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .airports import haversine_nm


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coord(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _add_fix(points: list[dict], ident, lat, lon, via: str = "") -> None:
    ident_text = str(ident or "").strip().upper()
    la, lo = _coord(lat), _coord(lon)
    if not ident_text or la is None or lo is None:
        return
    if abs(la) > 90 or abs(lo) > 180:
        return
    if points:
        last = points[-1]
        if last["ident"] == ident_text and abs(last["lat"] - la) < 0.01 and abs(last["lon"] - lo) < 0.01:
            return
    points.append({"ident": ident_text, "lat": la, "lon": lo, "via": str(via or "").strip().upper()})


def parse_waypoints(data: dict) -> list[dict]:
    """Navlog fixes plus origin/destination, with coordinates when SimBrief sends them."""
    points: list[dict] = []
    origin = data.get("origin") or {}
    dest = data.get("destination") or {}
    _add_fix(
        points,
        origin.get("icao_code") or origin.get("icao"),
        origin.get("pos_lat") or origin.get("latitude"),
        origin.get("pos_long") or origin.get("longitude"),
        "ORIG",
    )
    navlog = data.get("navlog") or {}
    for fix in _as_list(navlog.get("fix")):
        if not isinstance(fix, dict):
            continue
        _add_fix(
            points,
            fix.get("ident") or fix.get("name"),
            fix.get("pos_lat") or fix.get("latitude"),
            fix.get("pos_long") or fix.get("pos_lon") or fix.get("longitude"),
            fix.get("via_airway") or "",
        )
    _add_fix(
        points,
        dest.get("icao_code") or dest.get("icao"),
        dest.get("pos_lat") or dest.get("latitude"),
        dest.get("pos_long") or dest.get("longitude"),
        "DEST",
    )
    return points


def _to_xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    east = (lon - lon0) * 60.0 * math.cos(math.radians(lat0))
    north = (lat - lat0) * 60.0
    return east, north


def _along_nm(start: dict, end: dict, lat: float, lon: float) -> tuple[float, float]:
    bx, by = _to_xy(start["lat"], start["lon"], end["lat"], end["lon"])
    px, py = _to_xy(start["lat"], start["lon"], lat, lon)
    length = math.hypot(bx, by)
    if length < 0.05:
        return 0.0, 0.0
    along = (px * bx + py * by) / length
    return along, length


@dataclass
class NextWaypoint:
    ident: str
    distance_nm: float
    via: str
    previous: str

    def as_text(self) -> str:
        bits = [self.ident, f"{self.distance_nm:.0f} nm"]
        if self.via and self.via not in {"ORIG", "DEST", "DCT", "SID", "STAR"}:
            bits.append(f"via {self.via}")
        elif self.via == "DEST":
            bits.append("destination")
        if self.previous:
            bits.append(f"after {self.previous}")
        return "  ·  ".join(bits)


def next_waypoint(lat: float, lon: float, waypoints: list | None) -> NextWaypoint | None:
    """Next filed fix along the OFP, based on lat/lon. Not a GPS FMS substitute."""
    points = [item for item in (waypoints or []) if isinstance(item, dict) and "lat" in item and "lon" in item]
    if not points:
        return None
    if len(points) == 1:
        only = points[0]
        return NextWaypoint(only["ident"], haversine_nm(lat, lon, only["lat"], only["lon"]), only.get("via") or "", "")
    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        along, length = _along_nm(start, end, lat, lon)
        if along < length - 0.5:
            return NextWaypoint(
                end["ident"],
                haversine_nm(lat, lon, end["lat"], end["lon"]),
                end.get("via") or "",
                start["ident"],
            )
    last, prev = points[-1], points[-2]
    return NextWaypoint(last["ident"], haversine_nm(lat, lon, last["lat"], last["lon"]), last.get("via") or "DEST", prev["ident"])
