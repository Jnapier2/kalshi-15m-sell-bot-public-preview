#!/usr/bin/env python3
"""Maintainer-only deterministic preview manifest/checksum/archive builder."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from generate_sbom import generate as generate_sbom

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist"}
GENERATED = {"SHA256SUMS.txt", "MANIFEST.json"}
DEFAULT_RELEASE_TIMESTAMP = "2026-07-19T18:00:00Z"


def release_timestamp() -> str:
    value = os.getenv("SOURCE_DATE_EPOCH", "").strip()
    if not value:
        return DEFAULT_RELEASE_TIMESTAMP
    return datetime.fromtimestamp(int(value), timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_utf8_lf(path: Path, text: str) -> None:
    """Write deterministic UTF-8 bytes with LF line endings on every platform."""
    path.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def source_files(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.is_symlink():
            raise RuntimeError(f"Symlink cannot be released: {rel}")
        if path.is_file() and rel.as_posix() not in GENERATED:
            yield rel.as_posix(), path


def write_metadata(root: Path) -> dict[str, str]:
    records = {rel: sha256(path) for rel, path in source_files(root)}
    manifest = {
        "project": "kalshi-15m-sell-bot-public-preview",
        "version": "41.22.2",
        "generated_utc": release_timestamp(),
        "rights_holder": "Gateway Information Group LLC",
        "rights_notice": "Copyright © 2026 Gateway Information Group LLC. Licensed under the MIT License.",
        "license_status": "MIT",
        "publication_status": "PUBLIC_DRY_RUN_PREVIEW",
        "public_preview_only": True,
        "preview_engine_sha256": sha256(root / "kalshi_15m_sell_bot.py"),
        "release_lineage": "sanitized public-preview working tree; private workspace data excluded",
        "security_profile": "experimental preview; immutable dry run; all mutations blocked before signing; exact official origins",
        "files": [{"path": path, "sha256": digest} for path, digest in records.items()],
    }
    write_utf8_lf(root / "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    records["MANIFEST.json"] = sha256(root / "MANIFEST.json")
    write_utf8_lf(
        root / "SHA256SUMS.txt",
        "# SHA-256 inventory for every sealed release file except this checksum file.\n"
        + "".join(f"{digest}  {path}\n" for path, digest in sorted(records.items())),
    )
    # Rebuild MANIFEST one last time so it exactly matches checksum records, excluding itself to avoid recursion.
    manifest["files"] = [{"path": path, "sha256": digest} for path, digest in sorted(records.items()) if path != "MANIFEST.json"]
    write_utf8_lf(root / "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    # Update MANIFEST hash in sums after final write.
    records["MANIFEST.json"] = sha256(root / "MANIFEST.json")
    write_utf8_lf(
        root / "SHA256SUMS.txt",
        "# SHA-256 inventory for every sealed release file except this checksum file.\n"
        + "".join(f"{digest}  {path}\n" for path, digest in sorted(records.items())),
    )
    return records


def make_zip(root: Path, output: Path) -> None:
    epoch = (2026, 7, 18, 12, 0, 0)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, path in sorted((p.relative_to(root).as_posix(), p) for p in root.rglob("*") if p.is_file() and not any(part in IGNORED_DIRS for part in p.relative_to(root).parts)):
            info = zipfile.ZipInfo(f"kalshi-15m-sell-bot-public-preview/{rel}", date_time=epoch)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if os.access(path, os.X_OK) else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    generate_sbom(root, root / "SBOM.cdx.json")
    write_metadata(root)
    if args.output:
        make_zip(root, args.output.resolve())
        print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
