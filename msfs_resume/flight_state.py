"""Detect takeoff vs a completed flight (parked, engines off)."""

from __future__ import annotations

from dataclasses import dataclass

WAITING = "waiting"
RECORDING = "recording"
INTERRUPTED = "interrupted"

TAKEOFF = "takeoff"
COMPLETE = "complete"
INTERRUPT = "interrupt"
RESUME = "resume"

# ~1.2s at a 400ms UI tick; avoids a one-frame ground/engine glitch ending a flight.
PARKED_TICKS = 3
AIRBORNE_TICKS = 2


@dataclass
class PhaseUpdate:
    phase: str
    event: str | None


class FlightTracker:
    """Start recording once airborne; complete when back on the ground with engines off.

    A sim crash / return to the menu does not count as complete, so the last
    airborne snapshot stays available to restore.
    """

    def __init__(self, phase: str = WAITING) -> None:
        self.phase = phase
        self._airborne = 0
        self._parked_off = 0

    def reset(self, phase: str = WAITING) -> None:
        self.phase = phase
        self._airborne = 0
        self._parked_off = 0

    def update(self, *, in_world: bool, on_ground: bool, engines_running: bool) -> PhaseUpdate:
        if not in_world:
            self._airborne = 0
            self._parked_off = 0
            if self.phase == RECORDING:
                self.phase = INTERRUPTED
                return PhaseUpdate(self.phase, INTERRUPT)
            return PhaseUpdate(self.phase, None)

        airborne = not on_ground
        parked_off = on_ground and not engines_running

        if airborne:
            self._airborne += 1
            self._parked_off = 0
            if self._airborne >= AIRBORNE_TICKS:
                if self.phase == WAITING:
                    self.phase = RECORDING
                    return PhaseUpdate(self.phase, TAKEOFF)
                if self.phase == INTERRUPTED:
                    self.phase = RECORDING
                    return PhaseUpdate(self.phase, RESUME)
            return PhaseUpdate(self.phase, None)

        self._airborne = 0
        if parked_off:
            self._parked_off += 1
            if self.phase == RECORDING and self._parked_off >= PARKED_TICKS:
                self.phase = WAITING
                return PhaseUpdate(self.phase, COMPLETE)
            return PhaseUpdate(self.phase, None)

        # On the ground with engines running: taxi-out (not recording yet) or taxi-in.
        self._parked_off = 0
        return PhaseUpdate(self.phase, None)
