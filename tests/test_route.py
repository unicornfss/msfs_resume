import unittest

from msfs_resume.route import next_waypoint, parse_waypoints
from msfs_resume.simbrief import parse_ofp


class RouteTests(unittest.TestCase):
    def test_parse_navlog_and_airports(self) -> None:
        points = parse_waypoints(
            {
                "origin": {"icao_code": "egll", "pos_lat": "51.477", "pos_long": "-0.461"},
                "destination": {"icao_code": "lfpg", "pos_lat": "49.010", "pos_long": "2.548"},
                "navlog": {
                    "fix": [
                        {"ident": "DET", "pos_lat": "51.304", "pos_long": "0.597", "via_airway": "L9"},
                        {"ident": "DVR", "pos_lat": "51.163", "pos_long": "1.358", "via_airway": "L9"},
                    ]
                },
            }
        )
        self.assertEqual([p["ident"] for p in points], ["EGLL", "DET", "DVR", "LFPG"])

    def test_next_waypoint_between_fixes(self) -> None:
        points = [
            {"ident": "EGLL", "lat": 51.477, "lon": -0.461, "via": "ORIG"},
            {"ident": "DET", "lat": 51.304, "lon": 0.597, "via": "L9"},
            {"ident": "DVR", "lat": 51.163, "lon": 1.358, "via": "L9"},
        ]
        nxt = next_waypoint(51.38, 0.1, points)
        self.assertIsNotNone(nxt)
        assert nxt is not None
        self.assertEqual(nxt.ident, "DET")
        self.assertEqual(nxt.previous, "EGLL")

    def test_past_last_fix_is_destination(self) -> None:
        points = [
            {"ident": "DET", "lat": 51.304, "lon": 0.597, "via": "L9"},
            {"ident": "DVR", "lat": 51.163, "lon": 1.358, "via": "L9"},
        ]
        nxt = next_waypoint(51.16, 1.40, points)
        self.assertIsNotNone(nxt)
        assert nxt is not None
        self.assertEqual(nxt.ident, "DVR")

    def test_parse_ofp_keeps_waypoints(self) -> None:
        ofp = parse_ofp(
            {
                "origin": {"icao_code": "egll", "name": "Heathrow", "pos_lat": 51.477, "pos_long": -0.461},
                "destination": {"icao_code": "kjfk", "name": "Kennedy", "pos_lat": 40.64, "pos_long": -73.78},
                "general": {"icao_airline": "BAW", "flight_number": "117", "route": "DET L9 DVR"},
                "aircraft": {"icaocode": "B744"},
                "navlog": {"fix": {"ident": "DET", "pos_lat": 51.304, "pos_long": 0.597, "via_airway": "L9"}},
            }
        )
        self.assertEqual(ofp["waypoints"][0]["ident"], "EGLL")
        self.assertEqual(ofp["waypoints"][1]["ident"], "DET")


if __name__ == "__main__":
    unittest.main()
