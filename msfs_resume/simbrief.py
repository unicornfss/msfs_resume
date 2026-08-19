"""Fetch the latest SimBrief OFP for a username or numeric pilot ID."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

SIMBRIEF_URL = "https://www.simbrief.com/api/xml.fetcher.php"


class SimBriefError(RuntimeError):
    pass


def fetch_latest_ofp(ident: str, timeout: float = 12.0) -> dict:
    ident = ident.strip()
    if not ident:
        raise SimBriefError("No SimBrief username is set.")
    query_key = "userid" if ident.isdigit() else "username"
    url = f"{SIMBRIEF_URL}?{query_key}={urllib.parse.quote(ident)}&json=v2"
    request = urllib.request.Request(url, headers={"User-Agent": "MSFS-Resume"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise SimBriefError(f"SimBrief returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise SimBriefError(f"Could not reach SimBrief: {exc.reason}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SimBriefError("SimBrief returned data that was not JSON.") from exc
    if isinstance(data, dict):
        fetch = data.get("fetch") or {}
        status = str(fetch.get("status") or data.get("status") or "")
        if status.lower().startswith("error") or (
            status and status.lower() not in {"success", "ok"}
        ):
            raise SimBriefError(status)
    return parse_ofp(data)


def parse_ofp(data: dict) -> dict:
    origin = data.get("origin") or {}
    dest = data.get("destination") or {}
    general = data.get("general") or {}
    aircraft = data.get("aircraft") or {}
    airline = str(general.get("icao_airline") or "").strip()
    number = str(general.get("flight_number") or "").strip()
    flight_number = f"{airline}{number}".strip()
    origin_icao = origin.get("icao_code") or origin.get("icao") or ""
    dest_icao = dest.get("icao_code") or dest.get("icao") or ""
    aircraft_icao = (
        aircraft.get("icao_code")
        or aircraft.get("icaocode")
        or general.get("icao_id")
        or ""
    )
    return {
        "origin_icao": str(origin_icao).upper(),
        "origin_name": str(origin.get("name") or "").strip(),
        "dest_icao": str(dest_icao).upper(),
        "dest_name": str(dest.get("name") or "").strip(),
        "route": str(general.get("route") or "").strip(),
        "flight_number": flight_number,
        "aircraft_icao": str(aircraft_icao).upper(),
    }
