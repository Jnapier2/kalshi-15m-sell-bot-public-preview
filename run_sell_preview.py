"""Trusted local entrypoint; no credential, network, or trading capability."""
import sys
if __name__ == "__main__" and not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
    print("Use: python -I -S -B run_sell_preview.py [snapshot.json | --demo | --verify | --export | --menu]")
    raise SystemExit(2)
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = "41.84-public.1"
BUILD = "KALSELL-PUBLIC-41.84.1-OFFLINE-REPLACEMENT"
PACKAGE_ID = "KALSHI_15M_SELL_BOT_PUBLIC_PREVIEW"
MAX_INPUT = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_json(path, limit=MAX_INPUT):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("INPUT_TOO_LARGE")
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def verify_release():
    """Exact payload integrity, not a signature or an antivirus certification."""
    try:
        manifest = load_json(ROOT / "MANIFEST.json")
        files = manifest["files"]
        if manifest.get("schema") != "gateway-public-manifest-v2" or not isinstance(files, dict) or not 10 <= len(files) <= 80:
            raise ValueError("INVALID_MANIFEST")
        required = {"run_sell_preview.py", "VERSION.txt", "PACKAGE_METADATA.json", "SBOM.cdx.json", "LICENSE"}
        if not required.issubset(files) or "MANIFEST.json" in files:
            raise ValueError("MISSING_IDENTITY")
        observed = set()
        for base, directories, names in os.walk(ROOT, followlinks=False):
            relative = Path(base).relative_to(ROOT)
            if len(relative.parts) > 5:
                raise ValueError("UNEXPECTED_DEPTH")
            for directory in list(directories):
                child = Path(base) / directory
                if relative == Path(".") and directory in {".git", "outputs"}:
                    directories.remove(directory)
                elif child.is_symlink():
                    raise ValueError("LINK_REJECTED")
            for name in names:
                child = Path(base) / name
                if child.is_symlink():
                    raise ValueError("LINK_REJECTED")
                observed.add(child.relative_to(ROOT).as_posix())
                if len(observed) > 81:
                    raise ValueError("UNEXPECTED_FILES")
        if observed != set(files) | {"MANIFEST.json"}:
            raise ValueError("UNEXPECTED_FILES")
        for name, record in files.items():
            parts = name.split("/")
            if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) and part not in {".", ".."} for part in parts):
                raise ValueError("INVALID_MANIFEST_PATH")
            target = ROOT.joinpath(*parts)
            size = record["size"]
            if type(size) is not int or not 0 <= size <= 524288 or target.stat().st_size != size:
                raise ValueError("SIZE_MISMATCH")
            if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError("HASH_MISMATCH")
        metadata = load_json(ROOT / "PACKAGE_METADATA.json")
        if ((ROOT / "VERSION.txt").read_text().strip() != VERSION or
            metadata.get("display_version") != VERSION or metadata.get("build_id") != BUILD or
            metadata.get("package_id") != PACKAGE_ID or
            any(metadata.get(key) is not False for key in ("network_access", "credential_support", "live_write_capability"))):
            raise ValueError("IDENTITY_MISMATCH")
        return {"status": "PASS", "managed_files": len(files)}
    except Exception:
        # Never include exception text, paths, environment, or contents in diagnostics.
        return {"status": "FAIL", "code": "PACKAGE_INTEGRITY_FAILURE"}


def export_support(status="NOT_CHECKED"):
    """Bounded four-file export. No source, input, logs, environment, or rescan."""
    folder = ROOT
    for part in ("outputs", "support"):
        folder = folder / part
        if folder.is_symlink():
            raise ValueError("UNSAFE_OUTPUT")
        folder.mkdir(exist_ok=True)
        if not folder.is_dir():
            raise ValueError("UNSAFE_OUTPUT")
    receipt = {"schema": "public-export20-v1", "package_id": PACKAGE_ID,
               "version": VERSION, "build_id": BUILD, "integrity": status,
               "network_access": False, "input_collected": False, "file_count": 4}
    destination = folder / ("Export20_" + uuid.uuid4().hex + ".zip")
    try:
        with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("identity.json", json.dumps(receipt, indent=2) + "\n")
            archive.writestr("diagnostics.json", json.dumps({"integrity": status, "mode": "OFFLINE_ONLY"}) + "\n")
            archive.writestr("PRIVACY.txt", "No credentials, source files, input snapshots, account records, paths, or environment values collected.\n")
            archive.writestr("README.txt", "Minimal independent support export. NOT_CHECKED means no verification was requested. No scan or live action is performed.\n")
    except Exception:
        if destination.is_file() and not destination.is_symlink():
            destination.unlink()
        raise
    return destination.relative_to(ROOT).as_posix()


def report_export(status="NOT_CHECKED"):
    try:
        print(json.dumps({"status": "EXPORTED", "path": export_support(status)}))
        return 0
    except Exception:
        print(json.dumps({"status": "ERROR", "code": "EXPORT_FAILED"}))
        return 2


def main(args=None):
    args = list(sys.argv[1:] if args is None else args)
    if args == ["--export"]:
        return report_export()  # Independent of verification and planner imports.
    integrity = verify_release()
    if integrity["status"] != "PASS":
        print(json.dumps(integrity))
        report_export("FAIL")  # One bounded local capsule; never a recursive retry.
        return 2
    if args == ["--verify"]:
        print(json.dumps(integrity))
        return 0
    if args == ["--menu"]:
        while True:
            print("\nKalshi 15-Minute Sell Preview\nStart: [1] Synthetic demo\nReports: [2] Export20\nSetup: [3] Verify package\n[Q] Quit")
            try:
                action = input("Action: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return 0
            if action in {"", "q"}:
                return 0
            if action == "1":
                main(["--demo"])
            elif action == "2":
                report_export()
            elif action == "3":
                print(json.dumps(verify_release()))
            else:
                print("Choose 1, 2, 3, or Q.")
    if args in ([], ["--demo"]):
        path = ROOT / "examples" / "eligible_exit_snapshot.json"
    elif len(args) == 1 and not args[0].startswith("--"):
        path = Path(args[0])
        if not path.is_absolute():
            path = ROOT / path
    else:
        print(json.dumps({"status": "INVALID", "reason": "UNSUPPORTED_ARGUMENT"}))
        return 2
    try:
        snapshot = load_json(path)
        sys.path.insert(0, str(ROOT))  # Only after every managed payload has passed.
        from kalshi_sell_preview.planner import plan
        result = plan(snapshot)
        print(json.dumps(result, sort_keys=True))
        return 2 if result["status"] == "INVALID" else 0
    except Exception:
        print(json.dumps({"status": "INVALID", "reason": "INPUT_REJECTED"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
