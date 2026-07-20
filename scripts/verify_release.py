#!/usr/bin/env python3
"""Verify the sealed release inventory and SHA-256 hashes using only stdlib."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist"}
IGNORED_FILES = {"SHA256SUMS.txt"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_release_files(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.is_symlink():
            yield rel.as_posix(), path
        elif path.is_file() and rel.as_posix() not in IGNORED_FILES:
            yield rel.as_posix(), path


def load_checksums(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("SHA256SUMS.txt is missing or not a regular file")
    out: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"Malformed checksum line {number}") from exc
        if not HEX64.fullmatch(digest) or not rel or rel.startswith(("/", "../")) or "\\" in rel:
            raise ValueError(f"Unsafe checksum record on line {number}")
        if rel in out:
            raise ValueError(f"Duplicate checksum record: {rel}")
        out[rel] = digest
    return out


def verify(root: Path) -> list[str]:
    failures: list[str] = []
    root = root.resolve()
    expected = load_checksums(root / "SHA256SUMS.txt")
    actual: dict[str, Path] = {}
    for rel, path in iter_release_files(root):
        actual[rel] = path
        if path.is_symlink():
            failures.append(f"Symlink is not permitted in the release: {rel}")
        if path.suffix.lower() in {".pyc", ".pyo"}:
            failures.append(f"Bytecode is not permitted in the release: {rel}")
    missing = sorted(set(expected) - set(actual))
    unlisted = sorted(set(actual) - set(expected))
    failures.extend(f"Missing listed file: {rel}" for rel in missing)
    failures.extend(f"Unlisted release file: {rel}" for rel in unlisted)
    for rel in sorted(set(expected) & set(actual)):
        if actual[rel].is_symlink():
            continue
        digest = sha256_file(actual[rel])
        if digest != expected[rel]:
            failures.append(f"Hash mismatch: {rel}")
    manifest_path = root / "MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            records = {item["path"]: item["sha256"] for item in manifest.get("files", [])}
            expected_without_manifest = {path: digest for path, digest in expected.items() if path != "MANIFEST.json"}
            if records != expected_without_manifest:
                failures.append("MANIFEST.json file inventory does not match SHA256SUMS.txt")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            failures.append(f"MANIFEST.json is invalid: {exc}")
    else:
        failures.append("MANIFEST.json is missing")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        failures = verify(args.root)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] Release verification could not start: {exc}")
        return 1
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"Release integrity: FAIL ({len(failures)} issue(s))")
        return 1
    count = len(load_checksums(args.root.resolve() / "SHA256SUMS.txt"))
    print(f"[PASS] Release integrity and inventory verified ({count} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
