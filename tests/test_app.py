"""
Integration tests for app.py
============================
"""

import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


class TestAppIntegration(unittest.TestCase):
    def test_app_renders_without_exceptions(self):
        at = AppTest.from_file(APP_PATH, default_timeout=25)
        at.run()
        self.assertEqual(len(at.exception), 0, f"AppTest threw exceptions: {at.exception}")

    def test_app_tabs_and_elements_present(self):
        at = AppTest.from_file(APP_PATH, default_timeout=25)
        at.run()

        # Check main tabs exist (4 tabs)
        self.assertGreaterEqual(len(at.tabs), 4)

        # Check buttons exist (Crop selectors, analyze intent, etc.)
        self.assertGreaterEqual(len(at.button), 4)


if __name__ == "__main__":
    unittest.main()
