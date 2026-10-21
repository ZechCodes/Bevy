"""Prevent dependency and installer trust from regressing after CA distrust."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CaTrustTests(unittest.TestCase):
    def test_locked_certifi_excludes_distrusted_roots(self):
        lock = (ROOT / "poetry.lock").read_text()
        package = re.search(r'(?m)^name = "certifi"\nversion = "([^"\n]+)"', lock)
        self.assertIsNotNone(package, "certifi must remain explicitly locked")
        version = tuple(int(part) for part in package.group(1).split("."))
        self.assertGreaterEqual(version, (2026, 10, 19))


if __name__ == "__main__":
    unittest.main()
