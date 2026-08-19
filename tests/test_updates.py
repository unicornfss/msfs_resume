import unittest

from msfs_resume.updates import is_newer


class UpdateTests(unittest.TestCase):
    def test_is_newer(self) -> None:
        self.assertTrue(is_newer("0.4.0", "0.3.2"))
        self.assertTrue(is_newer("1.0.0", "0.9.9"))
        self.assertFalse(is_newer("0.4.0", "0.4.0"))
        self.assertFalse(is_newer("0.3.2", "0.4.0"))


if __name__ == "__main__":
    unittest.main()
