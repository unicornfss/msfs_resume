import unittest

from msfs_resume.aircraft import aircraft_compatible


class AircraftMatchTests(unittest.TestCase):
    def test_icao_in_title(self) -> None:
        self.assertTrue(aircraft_compatible("PMDG 737-800", "B738", "B738"))

    def test_family_737(self) -> None:
        self.assertTrue(aircraft_compatible("PMDG 737-800", "Boeing 737-800", "B738"))

    def test_mismatch(self) -> None:
        self.assertFalse(aircraft_compatible("Fenix A320", "PMDG 737-800", "B738"))

    def test_empty_saved_allows(self) -> None:
        self.assertTrue(aircraft_compatible("Anything", "", ""))


if __name__ == "__main__":
    unittest.main()
