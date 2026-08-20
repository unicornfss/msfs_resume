import unittest
from datetime import datetime, timedelta, timezone

from msfs_resume.snapshot import FlightSnapshot, consider_history, utc_now_iso


def _snap(*, hours=0, lat=51.0, lon=0.0) -> FlightSnapshot:
    saved = datetime.now(timezone.utc) - timedelta(hours=hours)
    return FlightSnapshot(
        saved_at=saved.replace(microsecond=0).isoformat(),
        aircraft="Test",
        latitude=lat,
        longitude=lon,
        altitude_ft=35000,
        heading_mag=270,
        heading_true=270,
        ias_kt=280,
        tas_kt=450,
        vertical_speed_fpm=0,
        pitch_deg=0,
        bank_deg=0,
        on_ground=False,
        fuel_lb=10000,
        fuel_gal=1500,
        fuel_capacity_gal=5000,
        fuel_lb_per_gal=6.7,
        engines_running=True,
        autopilot=True,
        qnh_mb=1013,
        zulu_year=2026,
        zulu_month=8,
        zulu_day=20,
        zulu_time_sec=12 * 3600,
        local_time_sec=13 * 3600,
    )


class HistoryTests(unittest.TestCase):
    def test_first_point(self) -> None:
        snap = _snap()
        self.assertEqual(consider_history(snap, []), [snap])

    def test_ignores_close_updates(self) -> None:
        first = _snap(hours=0)
        second = _snap(hours=0, lat=51.01)
        history = consider_history(first, [])
        history = consider_history(second, history)
        self.assertEqual(len(history), 1)

    def test_keeps_distant_point(self) -> None:
        first = _snap(hours=1, lat=51.0, lon=0.0)
        second = _snap(hours=0, lat=52.5, lon=1.5)
        history = consider_history(second, [first])
        self.assertEqual(len(history), 2)

    def test_force_pin(self) -> None:
        first = _snap(hours=0)
        second = _snap(hours=0, lat=51.001)
        history = consider_history(second, [first], force=True)
        self.assertEqual(len(history), 2)

    def test_caps_at_five(self) -> None:
        items = [_snap(hours=5 - i, lat=50 + i) for i in range(5)]
        extra = _snap(hours=0, lat=60)
        history = consider_history(extra, items, force=True)
        self.assertEqual(len(history), 5)
        self.assertEqual(history[-1].latitude, 60)

    def test_old_snapshot_without_qnh_loads(self) -> None:
        snap = FlightSnapshot.from_json(
            {
                "saved_at": utc_now_iso(),
                "aircraft": "Old",
                "latitude": 1,
                "longitude": 2,
                "altitude_ft": 1000,
                "heading_mag": 10,
                "heading_true": 10,
                "ias_kt": 120,
                "tas_kt": 130,
                "vertical_speed_fpm": 0,
                "pitch_deg": 0,
                "bank_deg": 0,
                "on_ground": False,
                "fuel_lb": 100,
                "fuel_gal": 15,
                "fuel_capacity_gal": 200,
                "fuel_lb_per_gal": 6.7,
                "engines_running": True,
                "autopilot": False,
            }
        )
        self.assertEqual(snap.qnh_mb, 0.0)
        self.assertEqual(snap.zulu_year, 0.0)


if __name__ == "__main__":
    unittest.main()
