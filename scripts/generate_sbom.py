#!/usr/bin/env python3
"""Generate a deterministic CycloneDX runtime SBOM from the sealed lock file."""
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_NAME = "kalshi-15m-sell-bot-public"
PROJECT_VERSION = "41.22.2"
DEFAULT_TIMESTAMP = "2026-07-19T18:00:00Z"
DIRECT = {"requests", "certifi", "cryptography", "websockets", "tzdata"}
LICENSES = {
    "certifi": "MPL-2.0",
    "cffi": "MIT-0",
    "charset-normalizer": "MIT",
    "cryptography": "Apache-2.0 OR BSD-3-Clause",
    "idna": "BSD-3-Clause",
    "pycparser": "BSD-3-Clause",
    "requests": "Apache-2.0",
    "tzdata": "Apache-2.0",
    "urllib3": "MIT",
    "websockets": "BSD-3-Clause",
}
DEPENDENCIES = {
    "requests": {"certifi", "charset-normalizer", "idna", "urllib3"},
    "cryptography": {"cffi", "typing-extensions"},
    "cffi": {"pycparser"},
    "certifi": set(),
    "charset-normalizer": set(),
    "idna": set(),
    "pycparser": set(),
    "tzdata": set(),
    "typing-extensions": set(),
    "urllib3": set(),
    "websockets": set(),
}
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_lock(path: Path) -> dict[str, str]:
    packages: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = PIN.match(raw.strip())
        if match:
            name = normalize(match.group(1))
            version = match.group(2)
            previous = packages.get(name)
            if previous and previous != version:
                raise ValueError(f"Conflicting versions for {name}: {previous} and {version}")
            packages[name] = version
    if not packages:
        raise ValueError("No exact package pins found in runtime lock")
    missing = DIRECT - set(packages)
    if missing:
        raise ValueError("Runtime lock is missing direct dependencies: " + ", ".join(sorted(missing)))
    return packages


def purl(name: str, version: str) -> str:
    return f"pkg:pypi/{name}@{version}"


def timestamp() -> str:
    value = os.getenv("SOURCE_DATE_EPOCH", "").strip()
    if not value:
        return DEFAULT_TIMESTAMP
    return datetime.fromtimestamp(int(value), timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate(root: Path, output: Path | None = None) -> Path:
    root = root.resolve()
    packages = parse_lock(root / "requirements.lock.txt")
    output = (output or root / "SBOM.cdx.json").resolve()
    project_ref = f"pkg:pypi/{PROJECT_NAME}@{PROJECT_VERSION}"
    components = []
    for name, version in sorted(packages.items()):
        license_expression = LICENSES.get(name)
        component = {
            "type": "library",
            "bom-ref": purl(name, version),
            "name": name,
            "version": version,
            "purl": purl(name, version),
            "scope": "required",
            "properties": [
                {"name": "release:dependency-kind", "value": "direct" if name in DIRECT else "transitive"},
                {"name": "release:version-source", "value": "requirements.lock.txt"},
            ],
        }
        if license_expression:
            component["licenses"] = [{"expression": license_expression}]
        components.append(component)

    dependency_records = [
        {"ref": project_ref, "dependsOn": [purl(name, packages[name]) for name in sorted(DIRECT)]}
    ]
    for name, version in sorted(packages.items()):
        children = [purl(child, packages[child]) for child in sorted(DEPENDENCIES.get(name, set())) if child in packages]
        dependency_records.append({"ref": purl(name, version), "dependsOn": children})

    serial_seed = "|".join(f"{name}=={version}" for name, version in sorted(packages.items()))
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, project_ref + '|' + serial_seed)}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp(),
            "component": {
                "type": "application",
                "bom-ref": project_ref,
                "name": PROJECT_NAME,
                "version": PROJECT_VERSION,
                "purl": project_ref,
                "licenses": [{"license": {"id": "MIT"}}],
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "stdlib deterministic SBOM generator",
                        "version": "1",
                    }
                ]
            },
            "properties": [
                {"name": "release:lock-file", "value": "requirements.lock.txt"},
                {"name": "release:network-used", "value": "false"},
            ],
        },
        "components": components,
        "dependencies": dependency_records,
    }
    output.write_bytes((json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    print(generate(args.root, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
