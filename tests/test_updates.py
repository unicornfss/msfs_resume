import unittest

from msfs_resume.updates import installer_asset, is_newer


class UpdateTests(unittest.TestCase):
    def test_is_newer(self) -> None:
        self.assertTrue(is_newer("0.4.0", "0.3.2"))
        self.assertTrue(is_newer("1.0.0", "0.9.9"))
        self.assertFalse(is_newer("0.4.0", "0.4.0"))
        self.assertFalse(is_newer("0.3.2", "0.4.0"))

    def test_picks_setup_exe(self) -> None:
        name, url = installer_asset(
            [
                {"name": "source.zip", "browser_download_url": "https://example/source.zip"},
                {"name": "MSFSResumeSetup-0.4.3.exe", "browser_download_url": "https://example/setup.exe"},
            ]
        )
        self.assertEqual(name, "MSFSResumeSetup-0.4.3.exe")
        self.assertEqual(url, "https://example/setup.exe")

    def test_no_asset(self) -> None:
        self.assertEqual(installer_asset([]), ("", ""))


if __name__ == "__main__":
    unittest.main()
