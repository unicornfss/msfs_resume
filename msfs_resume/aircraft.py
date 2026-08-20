"""Compare the live aircraft with the saved restore point."""

from __future__ import annotations

import re


def _family(text: str) -> set[str]:
    blob = text.upper()
    found: set[str] = set()
    checks = (
        ("737", ("737", "B73")),
        ("738", ("B738", "737-8")),
        ("320", ("A320", "A20N", "A319", "A321", "A32", "A21N", "A19N")),
        ("330", ("A330", "A332", "A333", "A339")),
        ("350", ("A350", "A359", "A35K")),
        ("777", ("777", "B77")),
        ("787", ("787", "B78")),
        ("747", ("747", "B74")),
        ("380", ("A380", "A388")),
        ("170", ("E170", "E175", "E190", "E195")),
        ("172", ("C172", "CESSNA 172")),
    )
    for family, needles in checks:
        if any(needle in blob for needle in needles):
            found.add(family)
    found.update(re.findall(r"[A-Z]{1,2}\d{2,4}[A-Z]?", blob))
    found.update(re.findall(r"\d{3}", blob))
    return {item for item in found if item}


def aircraft_compatible(live: str, saved_name: str, saved_icao: str = "") -> bool:
    live_u = (live or "").strip().upper()
    saved_u = (saved_name or "").strip().upper()
    icao = (saved_icao or "").strip().upper()
    if not live_u:
        return False
    if not saved_u and not icao:
        return True
    if icao and icao in live_u:
        return True
    if saved_u and (saved_u in live_u or live_u in saved_u):
        return True
    return bool(_family(live_u) & _family(f"{saved_u} {icao}"))
