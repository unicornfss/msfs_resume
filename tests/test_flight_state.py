import unittest

from msfs_resume.flight_state import (
    COMPLETE,
    INTERRUPT,
    INTERRUPTED,
    RECORDING,
    RESUME,
    TAKEOFF,
    WAITING,
    FlightTracker,
)


def _run(tracker: FlightTracker, ticks: int, **kwargs) -> list[str]:
    events = []
    for _ in range(ticks):
        event = tracker.update(**kwargs).event
        if event:
            events.append(event)
    return events


class FlightTrackerTests(unittest.TestCase):
    def test_takeoff_starts_recording(self) -> None:
        tracker = FlightTracker()
        events = _run(
            tracker, 2,
            in_world=True, on_ground=False, engines_running=True,
        )
        self.assertEqual(events, [TAKEOFF])
        self.assertEqual(tracker.phase, RECORDING)

    def test_taxi_out_does_not_record(self) -> None:
        tracker = FlightTracker()
        events = _run(
            tracker, 5,
            in_world=True, on_ground=True, engines_running=True,
        )
        self.assertEqual(events, [])
        self.assertEqual(tracker.phase, WAITING)

    def test_landing_with_engines_running_is_not_complete(self) -> None:
        tracker = FlightTracker(RECORDING)
        events = _run(
            tracker, 5,
            in_world=True, on_ground=True, engines_running=True,
        )
        self.assertEqual(events, [])
        self.assertEqual(tracker.phase, RECORDING)

    def test_parked_engines_off_completes_flight(self) -> None:
        tracker = FlightTracker(RECORDING)
        events = _run(
            tracker, 3,
            in_world=True, on_ground=True, engines_running=False,
        )
        self.assertEqual(events, [COMPLETE])
        self.assertEqual(tracker.phase, WAITING)

    def test_touch_and_go_does_not_complete(self) -> None:
        tracker = FlightTracker(RECORDING)
        _run(tracker, 1, in_world=True, on_ground=True, engines_running=True)
        _run(tracker, 2, in_world=True, on_ground=False, engines_running=True)
        self.assertEqual(tracker.phase, RECORDING)

    def test_leaving_world_interrupts_instead_of_completing(self) -> None:
        tracker = FlightTracker(RECORDING)
        events = _run(
            tracker, 1,
            in_world=False, on_ground=True, engines_running=False,
        )
        self.assertEqual(events, [INTERRUPT])
        self.assertEqual(tracker.phase, INTERRUPTED)

    def test_gate_after_crash_does_not_clear_restore(self) -> None:
        tracker = FlightTracker(INTERRUPTED)
        events = _run(
            tracker, 5,
            in_world=True, on_ground=True, engines_running=False,
        )
        self.assertEqual(events, [])
        self.assertEqual(tracker.phase, INTERRUPTED)

    def test_airborne_after_interrupt_resumes_recording(self) -> None:
        tracker = FlightTracker(INTERRUPTED)
        events = _run(
            tracker, 2,
            in_world=True, on_ground=False, engines_running=True,
        )
        self.assertEqual(events, [RESUME])
        self.assertEqual(tracker.phase, RECORDING)


if __name__ == "__main__":
    unittest.main()
