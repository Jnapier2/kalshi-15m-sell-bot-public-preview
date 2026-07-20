#!/usr/bin/env python3
"""Launcher for the experimental, permanently dry-run public preview.

Copyright © 2026 Gateway Information Group LLC. Licensed under the MIT License.
A separate public-use license has not yet been selected by the owner.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import certifi

from public_safety import (
    DEMO_BASE_URL,
    LIVE_BASE_URL,
    PUBLIC_PREVIEW_GUIDANCE,
    PUBLIC_PREVIEW_ONLY,
    PROJECT_ROOT,
    require_public_preview_dry_run,
    secure_directory,
    set_owner_only_permissions,
    user_config_root,
    user_data_root,
    validate_external_storage_directory,
    validate_kalshi_base_url,
    validate_outbound_rest_url,
    validate_owner_only_file,
    validate_private_key_path,
)

CONFIG_SCHEMA_VERSION = 1
CONFIG_PATH = user_config_root() / "config.json"
ENGINE_PATH = PROJECT_ROOT / "kalshi_15m_sell_bot.py"
SECURITY_CHECK_PATH = PROJECT_ROOT / "scripts" / "security_check.py"
VERIFY_RELEASE_PATH = PROJECT_ROOT / "scripts" / "verify_release.py"

_SECURITY_ENV_KEYS = {
    "ALLOW_SYSTEM_PROXY",
    "BOT_DATA_DIR",
    "BOT_EXPORT_DIR",
    "CRASH_REPORT_INCLUDE_SENSITIVE",
    "DRY_RUN",
    "FORCE_LIVE_RUN",
    "KALSHI_ACCESS_KEY",
    "KALSHI_ACCESS_KEY_ID",
    "KALSHI_API_KEY_ID",
    "KALSHI_BASE_URL",
    "KALSHI_KEY_FILE",
    "KALSHI_KEY_ID",
    "KALSHI_PRIVATE_KEY_FILE",
    "KALSHI_PRIVATE_KEY_PATH",
    "LIVE_TRADING_ACK",
    "RUN_AUTH_DIAGNOSTIC",
    "RUN_ONCE",
}

_INJECTION_ENV_KEYS = {
    "ALL_PROXY",
    "CURL_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NETRC",
    "NO_PROXY",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "all_proxy",
    "http_proxy",
    "https_proxy",
    "no_proxy",
}


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D401
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


def _print_header() -> None:
    print("Kalshi 15m Sell Bot — Experimental Dry-Run Preview")
    print("PUBLIC_PREVIEW_ONLY: order submission is permanently blocked")
    print()


def _load_config(*, required: bool = False) -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        if required:
            raise RuntimeError("No local configuration found. Run: python bot.py configure")
        return {}
    if CONFIG_PATH.is_symlink() or not CONFIG_PATH.is_file():
        raise RuntimeError("Configuration path must be a regular file")
    try:
        validate_owner_only_file(CONFIG_PATH, label="Configuration file")
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Local configuration could not be read: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise RuntimeError("Local configuration has an unsupported schema. Run configure again.")
    return data


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    secure_directory(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        set_owner_only_permissions(tmp)
        os.replace(tmp, path)
        set_owner_only_permissions(path)
    finally:
        tmp.unlink(missing_ok=True)


def _validate_rsa_key(path: Path) -> None:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError as exc:
        raise RuntimeError("Install dependencies first with the provided setup script.") from exc
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("Private key must be an unencrypted PEM private key created for Kalshi.") from exc
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
        raise RuntimeError("Private key must be RSA with a minimum size of 2048 bits.")


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _copy_key_to_secure_store(source: Path, environment: str) -> Path:
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("Private key source must be a regular file, not a link or folder.")
    if source.suffix.lower() not in {".key", ".pem"}:
        raise RuntimeError("Private key must use a .key or .pem extension.")
    if _inside(source, PROJECT_ROOT):
        raise RuntimeError(
            "The private key is inside the project folder. Move it to Downloads or another private folder, "
            "remove it from the repository, then run configure again."
        )
    if not 128 <= source.stat().st_size <= 128 * 1024:
        raise RuntimeError("Private key file size is outside the expected safe range.")
    _validate_rsa_key(source)
    secret_dir = secure_directory(user_config_root() / "secrets")
    destination = secret_dir / f"kalshi-{environment}.key"
    fd, tmp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=str(secret_dir))
    tmp = Path(tmp_name)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        set_owner_only_permissions(tmp)
        os.replace(tmp, destination)
        set_owner_only_permissions(destination)
    finally:
        tmp.unlink(missing_ok=True)
    return Path(validate_private_key_path(destination, repository_root=PROJECT_ROOT))


def _prompt(value: str | None, label: str, *, secret: bool = False) -> str:
    if value is not None:
        return value.strip()
    reader = getpass.getpass if secret else input
    return reader(f"{label}: ").strip()


def cmd_configure(args: argparse.Namespace) -> int:
    _print_header()
    current = _load_config(required=False)
    default_env = str(current.get("environment") or "demo")
    environment = (args.environment or "").strip().lower()
    if not environment:
        entered = input(f"Environment [demo/production] ({default_env}): ").strip().lower()
        environment = entered or default_env
    if environment not in {"demo", "production"}:
        raise RuntimeError("Environment must be demo or production.")

    existing_id = str(current.get("api_key_id") or "")
    api_key_id = _prompt(args.api_key_id, f"Kalshi {environment} API Key ID") or existing_id
    if not api_key_id or any(ch.isspace() for ch in api_key_id):
        raise RuntimeError("API Key ID is required and cannot contain whitespace.")
    if len(api_key_id) > 256:
        raise RuntimeError("API Key ID is unexpectedly long.")

    raw_key = _prompt(args.private_key, "Path to the downloaded .key or .pem file")
    if raw_key:
        source = Path(os.path.expandvars(raw_key)).expanduser().resolve(strict=True)
        stored_key = _copy_key_to_secure_store(source, environment)
    else:
        existing_path = str(current.get("private_key_path") or "")
        if not existing_path:
            raise RuntimeError("A private key path is required.")
        stored_key = Path(validate_private_key_path(existing_path, repository_root=PROJECT_ROOT))
        _validate_rsa_key(stored_key)

    instance = (args.instance or str(current.get("instance_name") or "PUBLIC")).strip() or "PUBLIC"
    allowed_instance_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"  # pragma: allowlist secret
    if len(instance) > 64 or any(ch not in allowed_instance_chars for ch in instance):
        raise RuntimeError("Instance name may contain only letters, numbers, hyphens, and underscores.")

    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "environment": environment,
        "api_key_id": api_key_id,
        "private_key_path": str(stored_key),
        "instance_name": instance,
    }
    _atomic_write_json(CONFIG_PATH, payload)
    print("Configuration saved outside the repository.")
    print(f"Environment : {environment}")
    print("API Key ID  : stored privately")
    print(f"Key file    : {stored_key.name} (private application storage)")
    print("Next step   : python bot.py run  # dry run is the default")
    return 0


def _validated_config() -> dict[str, Any]:
    config = _load_config(required=True)
    environment = str(config.get("environment") or "")
    if environment not in {"demo", "production"}:
        raise RuntimeError("Configured environment is invalid. Run configure again.")
    api_key_id = str(config.get("api_key_id") or "").strip()
    if not api_key_id or any(ch.isspace() for ch in api_key_id):
        raise RuntimeError("Configured API Key ID is invalid. Run configure again.")
    key_path = Path(validate_private_key_path(str(config.get("private_key_path") or ""), repository_root=PROJECT_ROOT))
    _validate_rsa_key(key_path)
    config["private_key_path"] = str(key_path)
    return config


def _child_environment(config: dict[str, Any], *, dry_run: bool, run_once: bool) -> dict[str, str]:
    require_public_preview_dry_run(dry_run)
    env = {key: value for key, value in os.environ.items() if key not in _SECURITY_ENV_KEYS and key not in _INJECTION_ENV_KEYS}
    environment = str(config["environment"])
    instance = str(config.get("instance_name") or "PUBLIC")
    data_dir = validate_external_storage_directory(
        user_data_root() / "runtime" / instance, repository_root=PROJECT_ROOT, label="BOT_DATA_DIR"
    )
    export_dir = validate_external_storage_directory(
        user_data_root() / "exports" / instance, repository_root=PROJECT_ROOT, label="BOT_EXPORT_DIR"
    )
    env.update(
        {
            "ALLOW_SYSTEM_PROXY": "0",
            "BOT_DATA_DIR": data_dir,
            "BOT_EXPORT_DIR": export_dir,
            "BOT_INSTANCE_NAME": instance,
            "CRASH_REPORT_INCLUDE_SENSITIVE": "0",
            "DRY_RUN": "1",
            "FORCE_LIVE_RUN": "0",
            "KALSHI_API_KEY_ID": str(config["api_key_id"]),
            "KALSHI_BASE_URL": DEMO_BASE_URL if environment == "demo" else LIVE_BASE_URL,
            "KALSHI_PRIVATE_KEY_PATH": str(config["private_key_path"]),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "RUN_AUTH_DIAGNOSTIC": "0",
            "RUN_ONCE": "1" if run_once else "0",
        }
    )
    return env


def _run_engine(config: dict[str, Any], *, dry_run: bool, run_once: bool) -> int:
    require_public_preview_dry_run(dry_run)
    if not ENGINE_PATH.is_file():
        raise RuntimeError("Engine file is missing. Verify or re-download the release.")
    env = _child_environment(config, dry_run=dry_run, run_once=run_once)
    completed = subprocess.run([sys.executable, str(ENGINE_PATH)], cwd=str(PROJECT_ROOT), env=env, check=False)
    return int(completed.returncode)


def _run_gate(*, include_tests: bool = True) -> bool:
    commands = [[sys.executable, str(VERIFY_RELEASE_PATH), "--root", str(PROJECT_ROOT)]]
    security_cmd = [sys.executable, str(SECURITY_CHECK_PATH), "--root", str(PROJECT_ROOT)]
    if include_tests:
        security_cmd.append("--strict")
    commands.append(security_cmd)
    for command in commands:
        completed = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
        if completed.returncode != 0:
            return False
    return True


def _online_demo_check() -> bool:
    url = validate_outbound_rest_url(DEMO_BASE_URL + "/exchange/status")
    context = ssl.create_default_context(cafile=certifi.where())
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    if hasattr(ssl, "TLSVersion"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context), NoRedirectHandler())
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "Kalshi15mSellBotPublic-Verify/1"})
    try:
        with opener.open(request, timeout=10) as response:
            code = int(getattr(response, "status", 0) or 0)
            if code != 200:
                print(f"[FAIL] Online demo endpoint returned HTTP {code}")
                return False
            payload = json.loads(response.read(1024 * 1024).decode("utf-8"))
            if not isinstance(payload, dict):
                print("[FAIL] Online demo endpoint returned an unexpected response")
                return False
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        print(f"[FAIL] Online demo endpoint check: {exc}")
        return False
    print("[PASS] Official Kalshi demo endpoint reached with TLS and redirects/proxies disabled")
    return True


def cmd_verify(args: argparse.Namespace) -> int:
    _print_header()
    ok = _run_gate(include_tests=not args.quick)
    if args.online:
        ok = _online_demo_check() and ok
    if ok:
        print("\nSECURITY GATE: PASS")
        print("This verifies this copy and its safeguards; it does not guarantee profits or eliminate trading risk.")
        return 0
    print("\nSECURITY GATE: FAIL")
    print("Do not configure credentials or run the preview until every failure is resolved.")
    return 1


def cmd_status(_args: argparse.Namespace) -> int:
    _print_header()
    config = _load_config(required=False)
    if not config:
        print("Configuration: not created")
        print("Run          : python bot.py configure")
        return 0
    environment = str(config.get("environment") or "invalid")
    key_path = Path(str(config.get("private_key_path") or ""))
    print(f"Configuration: {CONFIG_PATH}")
    print(f"Environment  : {environment}")
    print("API Key ID   : stored privately")
    print(f"Private key  : {'present' if key_path.is_file() and not key_path.is_symlink() else 'missing'} ({key_path.name or 'not set'})")
    print("Default run : dry run ON; one cycle")
    print(f"Preview lock: {'ON' if PUBLIC_PREVIEW_ONLY else 'INVALID'}; order submission is unavailable")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    _print_header()
    config = _validated_config()
    print(f"Mode        : DRY RUN ({config['environment']})")
    print(f"Duration    : {'continuous until stopped' if args.continuous else 'one cycle'}")
    print("Order writes: blocked in the engine before signing or network transmission")
    return _run_engine(config, dry_run=True, run_once=not args.continuous)


def cmd_live(_args: argparse.Namespace) -> int:
    _print_header()
    raise RuntimeError(PUBLIC_PREVIEW_GUIDANCE)


def cmd_run(args: argparse.Namespace) -> int:
    """Run the preview dry; legacy live switches return clear migration guidance."""
    if args.live:
        return cmd_live(argparse.Namespace())
    if args.production:
        raise RuntimeError("--production is valid only together with --live.")
    return cmd_dry_run(argparse.Namespace(continuous=bool(args.continuous)))


def cmd_menu(_args: argparse.Namespace) -> int:
    while True:
        _print_header()
        print("1. Verify this release (recommended first)")
        print("2. Configure demo credentials")
        print("3. Run one dry-run cycle")
        print("4. Show local status")
        print("5. Explain why order-capable mode is unavailable")
        print("Q. Quit")
        choice = input("Select: ").strip().lower()
        try:
            if choice == "1":
                cmd_verify(argparse.Namespace(quick=False, online=False))
            elif choice == "2":
                cmd_configure(argparse.Namespace(environment="demo", api_key_id=None, private_key=None, instance="PUBLIC"))
            elif choice == "3":
                cmd_dry_run(argparse.Namespace(continuous=False))
            elif choice == "4":
                cmd_status(argparse.Namespace())
            elif choice == "5":
                cmd_live(argparse.Namespace())
            elif choice in {"q", "quit", "exit"}:
                return 0
            else:
                print("Unknown selection.")
        except (RuntimeError, OSError, ValueError) as exc:
            print(f"\n[BLOCKED] {exc}")
        input("\nPress Enter to continue...")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental advanced dry-run learning preview; order submission is disabled")
    sub = parser.add_subparsers(dest="command")

    verify = sub.add_parser("verify", help="Verify hashes, source safeguards, and tests")
    verify.add_argument("--quick", action="store_true", help="Skip unit tests; integrity and static checks still run")
    verify.add_argument("--online", action="store_true", help="Also contact the official public demo status endpoint")
    verify.set_defaults(func=cmd_verify)

    configure = sub.add_parser("configure", help="Store credentials outside the repository")
    configure.add_argument("--environment", choices=("demo", "production"))
    configure.add_argument("--api-key-id")
    configure.add_argument("--private-key")
    configure.add_argument("--instance", default="PUBLIC")
    configure.set_defaults(func=cmd_configure)

    status = sub.add_parser("status", help="Show redacted local configuration status")
    status.set_defaults(func=cmd_status)

    run = sub.add_parser("run", help="Run the hard-blocked dry-run preview")
    run.add_argument("--live", action="store_true", help="Unavailable in this preview; prints flagship guidance")
    run.add_argument("--production", action="store_true", help="Unavailable with --live in this preview")
    run.add_argument("--continuous", action="store_true", help="Run continuously instead of one cycle")
    run.set_defaults(func=cmd_run)

    dry_run = sub.add_parser("dry-run", help="Read account/market data with all order writes blocked")
    dry_run.add_argument("--continuous", action="store_true", help="Run until stopped instead of one cycle")
    dry_run.set_defaults(func=cmd_dry_run)

    live = sub.add_parser("live", help="Unavailable in this preview; prints guidance to the reviewed 10x1c flagship")
    live.add_argument("--production", action="store_true", help="Accepted only to return the preview-only block message")
    live.add_argument("--continuous", action="store_true", help="Accepted only to return the preview-only block message")
    live.set_defaults(func=cmd_live)

    menu = sub.add_parser("menu", help="Open the interactive menu")
    menu.set_defaults(func=cmd_menu)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        if sys.stdin.isatty():
            return cmd_menu(argparse.Namespace())
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nStopped by user. No further action was taken.")
        return 130
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
