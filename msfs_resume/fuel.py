"""Fuel band used to gate a restore, matching the NewSky min/max idea."""

from __future__ import annotations

KG_PER_LB = 0.45359237
LB_PER_KG = 1.0 / KG_PER_LB

DEFAULT_TOLERANCE_PCT = 5.0
DEFAULT_FLOOR_KG = 100.0


def lb_to_kg(pounds: float) -> float:
    return pounds * KG_PER_LB


def kg_to_lb(kilograms: float) -> float:
    return kilograms * LB_PER_KG


def fuel_band(
    exact_kg: float,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
    floor_kg: float = DEFAULT_FLOOR_KG,
    capacity_kg: float | None = None,
) -> tuple[float, float]:
    """Return (min_kg, max_kg) around the last recorded fuel load."""
    exact = max(0.0, exact_kg)
    delta = max(exact * (max(0.0, tolerance_pct) / 100.0), max(0.0, floor_kg))
    low = max(0.0, exact - delta)
    high = exact + delta
    if capacity_kg is not None and capacity_kg > 0:
        high = min(high, capacity_kg)
    if high < low:
        high = low
    return low, high


def in_band(current_kg: float, low_kg: float, high_kg: float) -> bool:
    return low_kg - 0.5 <= current_kg <= high_kg + 0.5
