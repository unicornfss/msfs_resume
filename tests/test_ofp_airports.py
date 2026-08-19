import unittest

from msfs_resume.airports import Airport, haversine_nm, min_runway_ft, nearest_suitable
from msfs_resume.simbrief import parse_ofp
from msfs_resume.snapshot import FlightSnapshot, load_snapshot, save_snapshot, utc_now_iso


class SimBriefParseTests(unittest.TestCase):
    def test_parse_ofp_v2_shape(self) -> None:
        ofp = parse_ofp(
            {
                "origin": {"icao_code": "egll", "name": "Heathrow"},
                "destination": {"icao_code": "kjfk", "name": "Kennedy"},
                "general": {
                    "icao_airline": "BAW",
                    "flight_number": "117",
                    "route": "DET L9 DVR",
                },
                "aircraft": {"icaocode": "B744"},
            }
        )
        self.assertEqual(ofp["origin_icao"], "EGLL")
        self.assertEqual(ofp["dest_icao"], "KJFK")
        self.assertEqual(ofp["flight_number"], "BAW117")
        self.assertEqual(ofp["aircraft_icao"], "B744")
        self.assertEqual(ofp["route"], "DET L9 DVR")


class AirportTests(unittest.TestCase):
    def test_min_runway_by_type(self) -> None:
        self.assertEqual(min_runway_ft("PMDG 737-800"), 5500)
        self.assertEqual(min_runway_ft("B77W"), 7000)
        self.assertEqual(min_runway_ft("Cessna 172"), 3000)

    def test_nearest_filters_short_runways(self) -> None:
        airports = [
            Airport("XXXX", "Short", 51.5, -0.1, 3000, "small_airport"),
            Airport("EGLL", "Heathrow", 51.477, -0.461, 12802, "large_airport"),
            Airport("EGLC", "City", 51.505, 0.055, 4948, "medium_airport"),
        ]
        matches = nearest_suitable(51.47, -0.46, "B738", airports, limit=3)
        self.assertEqual([item[0].icao for item in matches], ["EGLL"])
        self.assertLess(matches[0][1], 5)

    def test_haversine_known_distance(self) -> None:
        # EGLL to EGKK is roughly 21 nm.
        nm = haversine_nm(51.4775, -0.4614, 51.1481, -0.1903)
        self.assertGreater(nm, 18)
        self.assertLess(nm, 26)


class SnapshotCompatTests(unittest.TestCase):
    def test_old_snapshot_without_ofp_still_loads(self) -> None:
        from pathlib import Path
        import json
        import tempfile

        payload = {
            "saved_at": utc_now_iso(),
            "aircraft": "Fenix A320",
            "latitude": 51.15,
            "longitude": -0.19,
            "altitude_ft": 12000,
            "heading_mag": 90,
            "heading_true": 88,
            "ias_kt": 250,
            "tas_kt": 280,
            "vertical_speed_fpm": 0,
            "pitch_deg": 0,
            "bank_deg": 0,
            "on_ground": False,
            "fuel_lb": 12000,
            "fuel_gal": 1800,
            "fuel_capacity_gal": 4000,
            "fuel_lb_per_gal": 6.7,
            "engines_running": True,
            "autopilot": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_snapshot(path)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.aircraft, "Fenix A320")
        self.assertFalse(loaded.has_ofp)
        loaded.apply_ofp({"origin_icao": "EGKK", "dest_icao": "LFPG", "route": "BIG", "flight_number": "EZY812", "aircraft_icao": "A320", "origin_name": "", "dest_name": ""})
        self.assertEqual(loaded.origin_icao, "EGKK")
        self.assertTrue(loaded.has_ofp)


if __name__ == "__main__":
    unittest.main()
