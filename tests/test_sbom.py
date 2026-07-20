from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def lock_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in (ROOT / "requirements.lock.txt").read_text(encoding="utf-8").splitlines():
        match = PIN.match(raw.strip())
        if match:
            pins[normalize(match.group(1))] = match.group(2)
    return pins


class SbomTests(unittest.TestCase):
    def test_sbom_is_cyclonedx_1_6(self) -> None:
        document = json.loads((ROOT / "SBOM.cdx.json").read_text(encoding="utf-8"))
        self.assertEqual(document["bomFormat"], "CycloneDX")
        self.assertEqual(document["specVersion"], "1.6")
        self.assertEqual(document["metadata"]["component"]["name"], "kalshi-15m-sell-bot-public")
        self.assertEqual(document["metadata"]["component"]["version"], "41.22.2")

    def test_sbom_components_match_runtime_lock(self) -> None:
        document = json.loads((ROOT / "SBOM.cdx.json").read_text(encoding="utf-8"))
        components = {normalize(item["name"]): str(item["version"]) for item in document["components"]}
        self.assertEqual(components, lock_pins())


if __name__ == "__main__":
    unittest.main()
