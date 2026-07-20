"""Small, independently testable safety boundary for the dry-run preview.

Copyright © 2026 Gateway Information Group LLC. Licensed under the MIT License.
A separate public-use license has not been selected by the owner.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent
LIVE_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
DEMO_BASE_URL = "https://external-api.demo.kalshi.co/trade-api/v2"
LIVE_WEBSOCKET_URL = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"
DEMO_WEBSOCKET_URL = "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2"
ALLOWED_REST_BASE_URLS = frozenset({LIVE_BASE_URL, DEMO_BASE_URL})
ALLOWED_WEBSOCKET_URLS = frozenset({LIVE_WEBSOCKET_URL, DEMO_WEBSOCKET_URL})

# This source package is intentionally non-order-capable.  It is a literal,
# non-environment-backed release control so stale shells, copied commands, and
# direct engine execution cannot turn writes on.  Removing or changing this
# sentinel creates a different, unreviewed build.
PUBLIC_PREVIEW_ONLY: Final[bool] = True
PUBLIC_PREVIEW_GUIDANCE: Final[str] = (
    "Order submission is unavailable in this experimental advanced dry-run "
    "learning preview. Use the separately reviewed 10x1c flagship for any "
    "order-capable workflow."
)


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _clean_exact_url(value: str, *, websocket: bool = False) -> str:
    value = str(value or "").strip().rstrip("/")
    parsed = urlsplit(value)
    expected_scheme = "wss" if websocket else "https"
    if parsed.scheme != expected_scheme or not parsed.hostname:
        raise ValueError(f"Only {expected_scheme.upper()} endpoints are permitted")
    if parsed.username or parsed.password or parsed.port is not None:
        raise ValueError("Credentials and explicit ports are not permitted in an endpoint")
    if parsed.query or parsed.fragment:
        raise ValueError("Endpoint query strings and fragments are not permitted")
    return value


def validate_kalshi_base_url(value: str) -> str:
    value = _clean_exact_url(value, websocket=False)
    if value not in ALLOWED_REST_BASE_URLS:
        raise ValueError("KALSHI_BASE_URL must be an exact official Kalshi demo or production API URL")
    return value


def validate_kalshi_websocket_url(value: str) -> str:
    value = _clean_exact_url(value, websocket=True)
    if value not in ALLOWED_WEBSOCKET_URLS:
        raise ValueError("WebSocket destination is not in the exact official allowlist")
    return value


def validate_api_path(path: str) -> str:
    value = str(path or "")
    if not value.startswith("/") or value.startswith("//"):
        raise ValueError("API path must be a single-host absolute path")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("API path cannot contain a host, query string, or fragment")
    if "\\" in value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("API path contains an unsafe character")
    if any(part in {".", ".."} for part in parsed.path.split("/")):
        raise ValueError("API path cannot contain dot segments")
    if re.search(r"%(?:00|23|2e|2f|3f|5c)", value, flags=re.IGNORECASE):
        raise ValueError("API path contains an unsafe percent-encoded delimiter")
    return value


def validate_outbound_rest_url(url: str) -> str:
    value = _clean_exact_url(url, websocket=False)
    for base in ALLOWED_REST_BASE_URLS:
        if value == base or value.startswith(base + "/"):
            suffix = value[len(base):] or "/"
            validate_api_path(suffix)
            return value
    raise ValueError("Outbound REST request is not addressed to an allowlisted Kalshi endpoint")


def require_public_preview_dry_run(dry_run: bool) -> bool:
    """Require the immutable preview sentinel and dry-run mode."""
    if PUBLIC_PREVIEW_ONLY is not True:
        raise RuntimeError("PUBLIC_PREVIEW_ONLY sentinel integrity check failed; refusing to continue.")
    if dry_run is not True:
        raise RuntimeError(PUBLIC_PREVIEW_GUIDANCE)
    return True


def block_public_preview_mutation(method: str, path: str) -> None:
    """Fail closed on every mutating request before signing or transmission."""
    if PUBLIC_PREVIEW_ONLY is not True:
        raise RuntimeError("PUBLIC_PREVIEW_ONLY sentinel integrity check failed; refusing to continue.")
    normalized_method = str(method or "").upper()
    if normalized_method != "GET":
        raise RuntimeError(f"PUBLIC_PREVIEW_ONLY blocked mutating request: {normalized_method} {path}. {PUBLIC_PREVIEW_GUIDANCE}")


def validate_sell_only_order_create(
    method: str, path: str, json_body: object, *, client_prefix: str
) -> bool:
    """Reject order-create payloads that are not provably generated as sells.

    Legacy order creates declare ``action=sell`` directly. Event-order V2 uses
    the YES book, so a YES-position sell is an ask while a NO-position sell is
    represented as a bid. The managed client-order ID encodes the contract side
    and lets this boundary verify that mapping before signing or transmission.
    """
    method = str(method or "").upper()
    normalized = str(path or "").split("?", 1)[0].rstrip("/") or "/"
    if method != "POST":
        return True

    legacy_paths = {"/portfolio/orders", "/portfolio/orders/batched"}
    event_paths = {"/portfolio/events/orders", "/portfolio/events/orders/batched"}
    if normalized not in legacy_paths | event_paths:
        return True

    if not isinstance(json_body, dict):
        raise ValueError("Sell-only order create requires a JSON object payload")
    if normalized.endswith("/batched"):
        orders = json_body.get("orders")
        if not isinstance(orders, list) or not orders:
            raise ValueError("Sell-only batch create requires a non-empty orders list")
    else:
        orders = [json_body]

    prefix = str(client_prefix or "").strip()
    if not prefix:
        raise ValueError("Sell-only order create requires a managed client-order prefix")

    for order in orders:
        if not isinstance(order, dict):
            raise ValueError("Sell-only order create contains a non-object order")
        client_order_id = str(order.get("client_order_id") or "")
        if normalized in legacy_paths:
            if str(order.get("action") or "").lower() != "sell":
                raise ValueError("Sell-only mode blocked a legacy order that was not action=sell")
            side = str(order.get("side") or "").lower()
            expected_prefix = f"{prefix}-{side}-lg-"
            if side not in {"yes", "no"} or not client_order_id.startswith(expected_prefix):
                raise ValueError("Sell-only mode blocked an unmanaged legacy order create")
            continue

        api_side = str(order.get("side") or "").lower()
        yes_prefix = f"{prefix}-yes-v2-"
        no_prefix = f"{prefix}-no-v2-"
        if client_order_id.startswith(yes_prefix):
            expected_api_side = "ask"
        elif client_order_id.startswith(no_prefix):
            expected_api_side = "bid"
        else:
            raise ValueError("Sell-only mode blocked an unmanaged event-order create")
        if api_side != expected_api_side:
            raise ValueError(
                "Sell-only mode blocked an event-order side that does not match the encoded contract side"
            )
    return True


def user_config_root() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif os.sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "kalshi15m-sell-bot"


def user_data_root() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif os.sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "kalshi15m-sell-bot"


def secure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)
    return path


def validate_external_storage_directory(
    path: str | os.PathLike[str], *, repository_root: Path = PROJECT_ROOT, label: str = "Storage"
) -> str:
    repo = repository_root.resolve()
    candidate = Path(path).expanduser().resolve(strict=False)
    if _inside(candidate, repo):
        raise ValueError(f"{label} cannot be stored inside the project folder")
    secure_directory(candidate)
    return str(candidate)


def validate_private_key_path(
    path: str | os.PathLike[str], *, repository_root: Path = PROJECT_ROOT
) -> str:
    raw = Path(os.path.expandvars(str(path or ""))).expanduser()
    if not raw.is_absolute():
        raw = user_config_root() / "secrets" / raw
    resolved = raw.resolve(strict=True)
    repo = repository_root.resolve()
    if _inside(resolved, repo):
        raise ValueError("Private keys cannot be stored inside the project folder")
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError("Private key path must be a regular file")
    if resolved.suffix.lower() not in {".key", ".pem"}:
        raise ValueError("Private key file must use a .key or .pem extension")
    size = resolved.stat().st_size
    if size < 128 or size > 128 * 1024:
        raise ValueError("Private key file size is outside the expected safe range")
    validate_owner_only_file(resolved, label="Private key")
    return str(resolved)


def set_owner_only_permissions(path: Path) -> None:
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def validate_owner_only_file(path: Path, *, label: str) -> None:
    """Fail closed when a sensitive local file is readable by other Unix users."""
    if os.name == "nt":
        return
    metadata = path.stat()
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise ValueError(f"{label} must be owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError(f"{label} permissions are too broad; expected owner read/write only (0600)")


def mask_identifier(value: str) -> str:
    value = str(value or "")
    if len(value) <= 8:
        return "configured" if value else "not configured"
    return value[:4] + "…" + value[-4:]


def redact_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        "[PRIVATE KEY REDACTED]",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"(?im)(KALSHI-(?:ACCESS-KEY|ACCESS-SIGNATURE|ACCESS-TIMESTAMP)\s*[:=]\s*)[^\s,;]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(
        r"(?im)((?:KALSHI_API_KEY_ID|KALSHI_PRIVATE_KEY_PATH)\s*[:=]\s*)[^\r\n]+",
        r"\1[REDACTED]",
        text,
    )
    return text
