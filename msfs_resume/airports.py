"""Nearest airport lookup using a cached OurAirports extract."""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .settings import APP_DIR, ensure_app_dir

AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
RUNWAYS_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"
CACHE_PATH = APP_DIR / "airports_cache.json"

WIDEBODY = (
    "A330", "A332", "A333", "A339", "A340", "A342", "A343", "A346",
    "A350", "A359", "A35K", "A380", "A388",
    "B747", "B744", "B748", "B767", "B772", "B77L", "B77W", "B773",
    "B787", "B788", "B789", "B78X", "MD11",
)
NARROWBODY = (
    "A318", "A319", "A320", "A321", "A20N", "A21N", "A19N",
    "B737", "B738", "B739", "B37M", "B38M", "B39M", "B3XM",
    "BCS1", "BCS3", "E170", "E175", "E190", "E195", "CRJ9", "CRJ7",
)


@dataclass
class Airport:
    icao: str
    name: str
    lat: float
    lon: float
    longest_ft: float
    kind: str


def min_runway_ft(aircraft: str) -> int:
    text = (aircraft or "").upper()
    if any(code in text for code in WIDEBODY) or "777" in text or "787" in text or "A350" in text:
        return 7000
    if (
        any(code in text for code in NARROWBODY)
        or "PMDG" in text
        or "FENIX" in text
        or "A32" in text
        or "737" in text
        or "A220" in text
    ):
        return 5500
    return 3000


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_nm = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r_nm * math.asin(min(1.0, math.sqrt(a)))


def load_cache(path: Path | None = None) -> list[Airport]:
    target = path or CACHE_PATH
    if not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    airports = []
    for row in raw:
        try:
            airports.append(
                Airport(
                    icao=row["icao"],
                    name=row.get("name", ""),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    longest_ft=float(row.get("longest_ft") or 0),
                    kind=row.get("kind", ""),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return airports


def nearest_suitable(
    lat: float,
    lon: float,
    aircraft: str,
    airports: list[Airport],
    limit: int = 3,
) -> list[tuple[Airport, float]]:
    needed = min_runway_ft(aircraft)
    ranked: list[tuple[Airport, float]] = []
    for airport in airports:
        if airport.longest_ft < needed:
            continue
        if abs(airport.lat) > 90 or abs(airport.lon) > 180:
            continue
        distance = haversine_nm(lat, lon, airport.lat, airport.lon)
        ranked.append((airport, distance))
    ranked.sort(key=lambda item: item[1])
    return ranked[:limit]


def refresh_cache(path: Path | None = None, timeout: float = 45.0) -> list[Airport]:
    ensure_app_dir()
    target = path or CACHE_PATH
    airports_csv = _download(AIRPORTS_URL, timeout)
    runways_csv = _download(RUNWAYS_URL, timeout)
    longest: dict[str, float] = {}
    reader = csv.DictReader(io.StringIO(runways_csv))
    for row in reader:
        ident = (row.get("airport_ident") or "").upper()
        if len(ident) != 4:
            continue
        if (row.get("closed") or "").lower() == "yes":
            continue
        try:
            length = float(row.get("length_ft") or 0)
        except ValueError:
            continue
        if length <= 0:
            continue
        longest[ident] = max(longest.get(ident, 0.0), length)

    payload = []
    reader = csv.DictReader(io.StringIO(airports_csv))
    for row in reader:
        ident = (row.get("ident") or "").upper()
        kind = row.get("type") or ""
        if len(ident) != 4 or kind not in {"large_airport", "medium_airport", "small_airport"}:
            continue
        if (row.get("scheduled_service") == "no") and kind == "small_airport":
            continue
        try:
            lat = float(row.get("latitude_deg") or "nan")
            lon = float(row.get("longitude_deg") or "nan")
        except ValueError:
            continue
        if math.isnan(lat) or math.isnan(lon):
            continue
        length = longest.get(ident, 0.0)
        if length <= 0:
            continue
        payload.append(
            {
                "icao": ident,
                "name": row.get("name") or ident,
                "lat": lat,
                "lon": lon,
                "longest_ft": length,
                "kind": kind,
            }
        )
    target.write_text(json.dumps(payload), encoding="utf-8")
    return load_cache(target)


def _download(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "MSFS-Resume"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")
