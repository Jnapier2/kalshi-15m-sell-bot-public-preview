#!/usr/bin/env python3
"""Reproducible local baseline gate for the dry-run preview."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from verify_release import verify

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".bat", ".sh", ".example", ".gitignore", ".gitattributes"}
FORBIDDEN_SUFFIXES = {".exe", ".dll", ".sys", ".scr", ".com", ".msi", ".pyd", ".so", ".dylib", ".key", ".pem", ".p12", ".pfx", ".pyc", ".pyo"}
ALLOWED_NETWORK_ORIGINS = {
    "https://external-api.kalshi.com/trade-api/v2",
    "https://external-api.demo.kalshi.co/trade-api/v2",
    "wss://external-api-ws.kalshi.com/trade-api/ws/v2",
    "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2",
}
SECRET_PATTERNS = {
    "private key material": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
}


def files(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.is_file() or path.is_symlink():
            yield rel, path


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _check_ast(path: Path, text: str, failures: list[str], *, test_file: bool = False) -> None:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        failures.append(f"Python syntax error in {path}: {exc}")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"eval", "exec"}:
                failures.append(f"Dynamic code execution in {path}:{node.lineno}")
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    failures.append(f"shell=True in {path}:{node.lineno}")
                if (
                    not test_file
                    and kw.arg == "verify"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is False
                ):
                    failures.append(f"TLS verification disabled in {path}:{node.lineno}")
                if (
                    not test_file
                    and kw.arg == "allow_redirects"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    failures.append(f"HTTP redirects enabled in {path}:{node.lineno}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"pickle", "marshal"}:
                    failures.append(f"Unsafe serialization import in {path}:{node.lineno}")
        if isinstance(node, ast.ImportFrom) and node.module in {"pickle", "marshal"}:
            failures.append(f"Unsafe serialization import in {path}:{node.lineno}")


def _check_lock(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"Missing hash-locked dependency file: {path.name}")
        return
    logical: list[str] = []
    carry = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        carry += (" " if carry else "") + stripped.rstrip("\\").strip()
        if not stripped.endswith("\\"):
            logical.append(carry)
            carry = ""
    if carry:
        logical.append(carry)
    package_lines = [line for line in logical if "==" in line and not line.startswith(("-r ", "--"))]
    if not package_lines:
        failures.append(f"No pinned packages found in {path.name}")
    for line in package_lines:
        if " --hash=sha256:" not in " " + line:
            failures.append(f"Unhashed package record in {path.name}: {line.split()[0]}")
        package = line.split()[0]
        if package.count("==") != 1:
            failures.append(f"Package is not exactly pinned in {path.name}: {package}")


def _normalized_package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _exact_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)")
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        name = _normalized_package_name(match.group(1))
        version = match.group(2)
        if name in pins and pins[name] != version:
            raise ValueError(f"Conflicting lock versions for {name}")
        pins[name] = version
    return pins


def _check_sbom(root: Path, failures: list[str]) -> None:
    path = root / "SBOM.cdx.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") != "1.6":
            failures.append("SBOM.cdx.json is not a CycloneDX 1.6 document")
            return
        pins = _exact_pins(root / "requirements.lock.txt")
        components: dict[str, str] = {}
        for item in document.get("components", []):
            if not isinstance(item, dict):
                raise ValueError("non-object component")
            name = _normalized_package_name(str(item.get("name", "")))
            version = str(item.get("version", ""))
            if not name or not version or name in components:
                raise ValueError("missing or duplicate component")
            components[name] = version
        if components != pins:
            failures.append("SBOM component inventory does not match requirements.lock.txt")
        metadata = document.get("metadata", {})
        application = metadata.get("component", {}) if isinstance(metadata, dict) else {}
        if application.get("name") != "kalshi-15m-sell-bot-public" or application.get("version") != "41.22.2":
            failures.append("SBOM application identity is incorrect")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        failures.append(f"SBOM.cdx.json is invalid: {exc}")


def run_checks(root: Path, strict: bool) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    passes: list[str] = []
    root = root.resolve()

    for rel, path in files(root):
        rel_text = rel.as_posix()
        if path.is_symlink():
            failures.append(f"Symlink present: {rel_text}")
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"Forbidden credential/binary/bytecode file: {rel_text}")
        text = _read_text(path)
        if text is None:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"Possible {label} in {rel_text}")
        if path.suffix == ".py":
            _check_ast(path, text, failures, test_file="tests" in rel.parts)
        if "tests" not in rel.parts and (path.suffix in {".py", ".sh", ".bat"} or path.name == ".env.example"):
            for url in re.findall(r"(?:https|wss)://[^\s\"'<>),]+", text):
                if url.rstrip("/") not in ALLOWED_NETWORK_ORIGINS:
                    failures.append(f"Unexpected executable-code URL in {rel_text}: {url}")

    if (root / "kalshi_15m_toolbox.py").exists():
        failures.append("Internal maintenance toolbox is present in public package")
    for retired in ("START_HERE.bat", "Run_Kalshi_2c_Sell_Bot.bat", "run_kalshi_15m_sell_bot.defaults.bat"):
        if (root / retired).exists():
            failures.append(f"Retired live-first launcher is present: {retired}")

    engine = (root / "kalshi_15m_sell_bot.py").read_text(encoding="utf-8")
    safety = (root / "public_safety.py").read_text(encoding="utf-8")
    launcher = (root / "bot.py").read_text(encoding="utf-8")
    required_markers = {
        "demo endpoint is default": 'os.getenv("KALSHI_BASE_URL", DEMO_BASE_URL)',
        "dry run cannot be environment-disabled": "DRY_RUN = True",
        "immutable preview sentinel is literal": "PUBLIC_PREVIEW_ONLY: Final[bool] = True",
        "engine startup enforces preview mode": "require_public_preview_dry_run(DRY_RUN)",
        "final mutation boundary blocks preview writes": "block_public_preview_mutation(method, path)",
        "REST destination is validated": "validate_outbound_rest_url",
        "redirects are disabled": 'kwargs["allow_redirects"] = False',
        "pinned CA bundle is forced": 'kwargs["verify"] = PUBLIC_CA_BUNDLE',
        "WebSocket TLS context is explicit": 'ws_kwargs["ssl"] = create_public_tls_context()',
        "environment proxies are disabled": 'session.trust_env = False',
        "support ZIPs are bounded": "SUPPORT_ZIP_MAX_COMPRESSION_RATIO",
        "crash reports are private by default": 'os.getenv("CRASH_REPORT_INCLUDE_SENSITIVE", "0")',
        "private key is external": "validate_private_key_path",
        "launcher strips proxy variables": '"HTTPS_PROXY"',
        "launcher enforces preview-only dry run": "require_public_preview_dry_run(dry_run)",
        "public runtime is fixed sell-only": "PUBLIC_SELL_ONLY_MODE = True",
        "buy action planning is disabled": "BUY_ACTION_PLAN_ENABLED = False",
    }
    combined = engine + "\n" + safety + "\n" + launcher
    for label, marker in required_markers.items():
        if marker not in combined:
            failures.append(f"Missing required security marker: {label}")
    for forbidden in ('--ack', 'args.ack', 'REQUIRED_LIVE_TRADING_ACK'):
        if forbidden in launcher:
            failures.append(f"Removed live-ack bypass marker remains in launcher: {forbidden}")
    stale_bug_markers = ("central_time_filename_suffix()", "strike_key_from_ticker(", "strike_bucket_from_key(")
    for marker in stale_bug_markers:
        if marker in engine:
            failures.append(f"Known inherited undefined-name marker remains: {marker}")

    gitignore = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    for marker in ("*.key", "*.pem", ".env", "logs/", "exports/", "*.sqlite3"):
        if marker not in gitignore:
            failures.append(f".gitignore is missing security pattern: {marker}")

    _check_lock(root / "requirements.lock.txt", failures)
    _check_lock(root / "requirements-dev.lock.txt", failures)
    _check_sbom(root, failures)
    try:
        failures.extend(verify(root))
    except (OSError, ValueError) as exc:
        failures.append(f"Release integrity check failed to start: {exc}")

    if strict:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=str(root),
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            failures.append("Unit test suite failed")
        else:
            passes.append("Unit test suite")
    return failures, passes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="Also run the complete unit-test suite")
    args = parser.parse_args(argv)
    failures, passes = run_checks(args.root, args.strict)
    if failures:
        for index, _failure in enumerate(failures, start=1):
            print(f"[ACTION] Security check {index} needs review; details remain in process memory.")
        print(f"Security gate: ACTION NEEDED ({len(failures)} check(s))")
        return 1
    print("[PASS] Secret/binary surface scan")
    print("[PASS] Python syntax and prohibited-call scan")
    print("[PASS] Demo/hard-blocked-dry-run/sell-only/network/storage/archive/privacy baseline safeguards")
    print("[PASS] Hash-locked dependency policy and SBOM consistency")
    print("[PASS] Release inventory and SHA-256 verification")
    for item in passes:
        print(f"[PASS] {item}")
    print("Security gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
