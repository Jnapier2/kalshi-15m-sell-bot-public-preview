from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify_release import verify


class ReleaseIntegrityTests(unittest.TestCase):
    def test_current_release_verifies_when_sealed(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / "SHA256SUMS.txt").exists():
            self.skipTest("Release metadata has not been generated yet")
        self.assertEqual(verify(root), [])

    def test_unlisted_file_is_detected(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / "SHA256SUMS.txt").exists():
            self.skipTest("Release metadata has not been generated yet")
        marker = root / "UNLISTED_TEST_MARKER.tmp"
        marker.write_text("test", encoding="utf-8")
        try:
            self.assertTrue(any("Unlisted release file" in item for item in verify(root)))
        finally:
            marker.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
