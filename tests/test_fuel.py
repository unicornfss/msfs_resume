import unittest

from msfs_resume.fuel import fuel_band, in_band, kg_to_lb, lb_to_kg
from msfs_resume.snapshot import FlightSnapshot, clear_snapshot, load_snapshot, save_snapshot, utc_now_iso


class FuelTests(unittest.TestCase):
    def test_lb_kg_roundtrip(self) -> None:
        self.assertAlmostEqual(lb_to_kg(1000), 453.59237, places=5)
        self.assertAlmostEqual(kg_to_lb(1000), 2204.6226218, places=4)

    def test_fuel_band_percent_and_floor(self) -> None:
        low, high = fuel_band(8420, tolerance_pct=5, floor_kg=100, capacity_kg=20_000)
        self.assertEqual(round(low), 7999)
        self.assertEqual(round(high), 8841)

    def test_fuel_band_uses_floor_when_percent_is_tiny(self) -> None:
        low, high = fuel_band(500, tolerance_pct=5, floor_kg=100)
        self.assertEqual(low, 400)
        self.assertEqual(high, 600)

    def test_fuel_band_clamps_to_capacity(self) -> None:
        low, high = fuel_band(950, tolerance_pct=20, floor_kg=50, capacity_kg=1000)
        self.assertEqual(low, 760)
        self.assertEqual(high, 1000)

    def test_in_band_allows_half_kilo_slack(self) -> None:
        self.assertTrue(in_band(7998.6, 7999, 8841))
        self.assertFalse(in_band(7000, 7999, 8841))


class SnapshotTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        snap = FlightSnapshot(
            saved_at=utc_now_iso(),
            aircraft="PMDG 737-800",
            latitude=51.47,
            longitude=-0.46,
            altitude_ft=35000,
            heading_mag=274.2,
            heading_true=271.0,
            ias_kt=278,
            tas_kt=450,
            vertical_speed_fpm=0,
            pitch_deg=1.5,
            bank_deg=0.0,
            on_ground=False,
            fuel_lb=18563,
            fuel_gal=2770,
            fuel_capacity_gal=6875,
            fuel_lb_per_gal=6.7,
            engines_running=True,
            autopilot=True,
        )
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            save_snapshot(snap, path)
            loaded = load_snapshot(path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            clear_snapshot(path)
            self.assertFalse(path.exists())
            self.assertIsNone(load_snapshot(path))
        self.assertEqual(loaded.aircraft, "PMDG 737-800")
        self.assertAlmostEqual(loaded.fuel_kg, lb_to_kg(18563), places=3)
        self.assertGreater(loaded.capacity_kg or 0, 20_000)


if __name__ == "__main__":
    unittest.main()
