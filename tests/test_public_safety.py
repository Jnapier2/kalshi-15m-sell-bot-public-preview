from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import public_safety as safety


class PublicSafetyTests(unittest.TestCase):
    def test_demo_rest_endpoint_allowed(self):
        self.assertEqual(safety.validate_kalshi_base_url(safety.DEMO_BASE_URL), safety.DEMO_BASE_URL)

    def test_live_rest_endpoint_allowed(self):
        self.assertEqual(safety.validate_kalshi_base_url(safety.LIVE_BASE_URL), safety.LIVE_BASE_URL)

    def test_custom_rest_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            safety.validate_kalshi_base_url("https://example.invalid/trade-api/v2")

    def test_endpoint_userinfo_rejected(self):
        with self.assertRaises(ValueError):
            safety.validate_kalshi_base_url("https://example-user@external-api.kalshi.com/trade-api/v2")

    def test_endpoint_port_rejected(self):
        with self.assertRaises(ValueError):
            safety.validate_kalshi_base_url("https://external-api.kalshi.com:443/trade-api/v2")

    def test_api_path_accepts_normal_path(self):
        self.assertEqual(safety.validate_api_path("/portfolio/balance"), "/portfolio/balance")

    def test_api_path_rejects_missing_slash(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("portfolio/balance")

    def test_api_path_rejects_scheme_relative_host(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("//example.invalid/path")

    def test_api_path_rejects_dot_segment(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("/a/../b")

    def test_api_path_rejects_encoded_traversal(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("/a/%2e%2e/b")

    def test_api_path_rejects_encoded_slash(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("/a/%2F/b")

    def test_api_path_rejects_query(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("/markets?limit=1")

    def test_api_path_rejects_backslash(self):
        with self.assertRaises(ValueError):
            safety.validate_api_path("/a\\b")

    def test_outbound_url_requires_exact_prefix_boundary(self):
        with self.assertRaises(ValueError):
            safety.validate_outbound_rest_url(safety.DEMO_BASE_URL + ".example.invalid/exchange/status")

    def test_preview_sentinel_is_literal_and_requires_dry_run(self):
        self.assertIs(safety.PUBLIC_PREVIEW_ONLY, True)
        self.assertTrue(safety.require_public_preview_dry_run(True))
        with self.assertRaisesRegex(RuntimeError, "10x1c flagship"):
            safety.require_public_preview_dry_run(False)

    def test_preview_blocks_mutations_independent_of_acknowledgment(self):
        self.assertIsNone(safety.block_public_preview_mutation("GET", "/portfolio/balance"))
        with mock.patch.dict(os.environ, {"DRY_RUN": "0", "FORCE_LIVE_RUN": "1", "LIVE_TRADING_ACK": "anything"}):
            with self.assertRaisesRegex(RuntimeError, "PUBLIC_PREVIEW_ONLY blocked"):
                safety.block_public_preview_mutation("POST", "/portfolio/orders")

    def test_external_storage_rejects_repo(self):
        with self.assertRaises(ValueError):
            safety.validate_external_storage_directory(safety.PROJECT_ROOT / "runtime-test")

    def test_external_storage_accepts_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "data"
            result = safety.validate_external_storage_directory(candidate)
            self.assertTrue(Path(result).is_dir())


    @unittest.skipIf(os.name == "nt", "Unix permission bits are not authoritative on Windows")
    def test_private_key_permissions_must_be_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "sample.key"
            key.write_bytes(b"x" * 256)
            key.chmod(0o644)
            with self.assertRaises(ValueError):
                safety.validate_private_key_path(key)
            key.chmod(0o600)
            self.assertEqual(safety.validate_private_key_path(key), str(key.resolve()))

    def test_mask_identifier_never_returns_full_value(self):
        raw = "abcdefghijklmnop"
        masked = safety.mask_identifier(raw)
        self.assertNotEqual(masked, raw)
        self.assertIn("…", masked)

    def test_redaction_removes_header_values(self):
        text = "KALSHI-ACCESS-KEY: abcdef\nKALSHI-ACCESS-SIGNATURE=secretvalue"
        redacted = safety.redact_text(text)
        self.assertNotIn("abcdef", redacted)
        self.assertNotIn("secretvalue", redacted)

    def test_sell_only_validator_rejects_legacy_buy(self):
        with self.assertRaisesRegex(ValueError, "not action=sell"):
            safety.validate_sell_only_order_create(
                "POST", "/portfolio/orders",
                {"action": "buy", "side": "yes", "client_order_id": "K15M-yes-lg-abc"},
                client_prefix="K15M",
            )

    def test_sell_only_validator_accepts_managed_legacy_sell(self):
        self.assertTrue(safety.validate_sell_only_order_create(
            "POST", "/portfolio/orders",
            {"action": "sell", "side": "no", "client_order_id": "K15M-no-lg-abc"},
            client_prefix="K15M",
        ))

    def test_sell_only_validator_checks_v2_contract_side_mapping(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            safety.validate_sell_only_order_create(
                "POST", "/portfolio/events/orders",
                {"side": "bid", "client_order_id": "K15M-yes-v2-abc"},
                client_prefix="K15M",
            )
        self.assertTrue(safety.validate_sell_only_order_create(
            "POST", "/portfolio/events/orders",
            {"side": "bid", "client_order_id": "K15M-no-v2-abc"},
            client_prefix="K15M",
        ))


if __name__ == "__main__":
    unittest.main()
