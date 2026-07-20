from __future__ import annotations

import importlib
import json
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from public_safety import DEMO_BASE_URL


class _Response:
    status_code = 200
    text = "{}"

    def json(self):
        return {}


class _Session:
    def __init__(self):
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return _Response()


class EngineGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        env = {
            "BOT_DATA_DIR": str(root / "data"),
            "BOT_EXPORT_DIR": str(root / "exports"),
            "KALSHI_BASE_URL": DEMO_BASE_URL,
            "DRY_RUN": "0",
            "FORCE_LIVE_RUN": "1",
            "LIVE_TRADING_ACK": "anything",
            "ALLOW_SYSTEM_PROXY": "0",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            cls.engine = importlib.import_module("kalshi_15m_sell_bot")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_engine_defaults_demo_and_dry_run(self):
        self.assertEqual(self.engine.BASE_URL, DEMO_BASE_URL)
        self.assertTrue(self.engine.DRY_RUN)
        self.assertFalse(self.engine.FORCE_LIVE_RUN)
        self.assertTrue(self.engine.PUBLIC_PREVIEW_ONLY)
        self.assertFalse(self.engine.ALLOW_SYSTEM_PROXY)

    def test_http_wrapper_forces_tls_and_no_redirects(self):
        fake = _Session()
        old = self.engine.SESSION
        self.engine.SESSION = fake
        try:
            self.engine.http_session_request("GET", DEMO_BASE_URL + "/exchange/status", timeout=1)
        finally:
            self.engine.SESSION = old
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["verify"], self.engine.PUBLIC_CA_BUNDLE)
        self.assertIs(fake.calls[0]["allow_redirects"], False)

    def test_http_wrapper_rejects_tls_disable(self):
        with self.assertRaises(RuntimeError):
            self.engine.http_session_request("GET", DEMO_BASE_URL + "/exchange/status", verify=False)

    def test_http_wrapper_rejects_redirect_enable(self):
        with self.assertRaises(RuntimeError):
            self.engine.http_session_request("GET", DEMO_BASE_URL + "/exchange/status", allow_redirects=True)


    def test_http_wrapper_rejects_custom_ca_and_proxy(self):
        with self.assertRaises(RuntimeError):
            self.engine.http_session_request("GET", DEMO_BASE_URL + "/exchange/status", verify="/tmp/custom-ca.pem")  # nosec B108
        with self.assertRaises(RuntimeError):
            self.engine.http_session_request(
                "GET",
                DEMO_BASE_URL + "/exchange/status",
                proxies={"https": "https://proxy.invalid"},
            )

    def test_http_session_ignores_environment_and_uses_pinned_ca(self):
        self.assertFalse(self.engine.SESSION.trust_env)
        with mock.patch.object(self.engine.SESSION, "request", return_value=mock.Mock(status_code=200)) as request:
            self.engine.http_session_request("GET", DEMO_BASE_URL + "/exchange/status")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["verify"], self.engine.PUBLIC_CA_BUNDLE)
        self.assertEqual(kwargs["proxies"], {})
        self.assertFalse(kwargs["allow_redirects"])

    def test_http_wrapper_rejects_unapproved_host(self):
        with self.assertRaises(ValueError):
            self.engine.http_session_request("GET", "https://example.invalid/trade-api/v2/exchange/status")

    def test_dry_run_blocks_mutation_before_signing(self):
        old_dry = self.engine.DRY_RUN
        self.engine.DRY_RUN = True
        try:
            with mock.patch.object(self.engine, "create_signature") as signer:
                with self.assertRaisesRegex(RuntimeError, "PUBLIC_PREVIEW_ONLY blocked"):
                    self.engine.signed_request_at_base(DEMO_BASE_URL, "POST", "/portfolio/orders", json_body={})
            signer.assert_not_called()
        finally:
            self.engine.DRY_RUN = old_dry

    def test_runtime_flag_mutation_cannot_bypass_preview(self):
        old_dry = self.engine.DRY_RUN
        old_force = self.engine.FORCE_LIVE_RUN
        self.engine.DRY_RUN = False
        self.engine.FORCE_LIVE_RUN = True
        try:
            with mock.patch.object(self.engine, "create_signature") as signer:
                with self.assertRaisesRegex(RuntimeError, "10x1c flagship"):
                    self.engine.signed_request_at_base(DEMO_BASE_URL, "POST", "/portfolio/orders", json_body={})
            signer.assert_not_called()
        finally:
            self.engine.DRY_RUN = old_dry
            self.engine.FORCE_LIVE_RUN = old_force

    def test_websocket_url_is_official_demo(self):
        self.assertEqual(self.engine.websocket_url(), self.engine.DEMO_WEBSOCKET_URL)

    def test_legacy_order_payload_is_sell_only(self):
        payload = self.engine.create_sell_order_payload(
            "TEST-TICKER", "yes", self.engine.Decimal("1.00"), "good_till_canceled",
            use_reduce_only=False, use_sell_position_floor=True, post_only=True, exit_price=self.engine.Decimal("0.20")
        )
        self.assertEqual(payload["action"], "sell")

    def test_public_mode_disables_buy_planning_modules(self):
        self.assertTrue(self.engine.PUBLIC_SELL_ONLY_MODE)
        self.assertFalse(self.engine.BUY_ACTION_PLAN_ENABLED)
        self.assertFalse(self.engine.BUY_ACTION_PLAN_V2_HANDOFF_ENABLED)
        self.assertFalse(self.engine.BUY_SIDE_SIGNAL_EXPORT_ENABLED)
        self.assertFalse(self.engine.PROFIT_MINER_PLAN_ENABLED)
        self.assertFalse(self.engine.ENTRY_LADDER_PLAN_ENABLED)

    def test_preview_boundary_rejects_legacy_buy_before_signing(self):
        old_dry = self.engine.DRY_RUN
        self.engine.DRY_RUN = False
        try:
            with mock.patch.object(self.engine, "create_signature") as signer:
                with self.assertRaisesRegex(RuntimeError, "PUBLIC_PREVIEW_ONLY blocked"):
                    self.engine.signed_request_at_base(
                        DEMO_BASE_URL, "POST", "/portfolio/orders",
                        json_body={
                            "action": "buy", "side": "yes",
                            "client_order_id": f"{self.engine.CLIENT_PREFIX}-yes-lg-test",
                        },
                    )
            signer.assert_not_called()
        finally:
            self.engine.DRY_RUN = old_dry

    def test_safe_zip_extracts_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "safe.zip"
            target = Path(tmp) / "target"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("reports/sample.csv", "a,b\n1,2\n")
            result = Path(self.engine._extract_support_zip_to_temp(str(archive), str(target)))
            self.assertEqual((result / "reports" / "sample.csv").read_text(), "a,b\n1,2\n")

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "no")
            with self.assertRaises(ValueError):
                self.engine._extract_support_zip_to_temp(str(archive), str(Path(tmp) / "target"))

    def test_zip_symlink_rejected(self):
        if os.name == "nt":
            self.skipTest("Unix mode bits are not reliable on Windows ZIP writers")
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "link.zip"
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(info, "target")
            with self.assertRaises(ValueError):
                self.engine._extract_support_zip_to_temp(str(archive), str(Path(tmp) / "target"))

    def test_zip_bomb_ratio_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ratio.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("repeated.txt", b"0" * 400_000)
            with self.assertRaises(ValueError):
                self.engine._extract_support_zip_to_temp(str(archive), str(Path(tmp) / "target"))

    def test_known_undefined_name_markers_removed(self):
        source = Path(self.engine.__file__).read_text(encoding="utf-8")
        self.assertNotIn("central_time_filename_suffix()", source)
        self.assertNotIn("strike_key_from_ticker(", source)
        self.assertNotIn("strike_bucket_from_key(", source)

    def test_windows_process_probe_uses_system32_tasklist(self):
        source = Path(self.engine.__file__).read_text(encoding="utf-8")
        self.assertIn('os.path.join(system_root, "System32", "tasklist.exe")', source)
        self.assertNotIn('subprocess.run(["tasklist"', source)

    def test_crash_reports_default_to_summary_only(self):
        source = Path(self.engine.__file__).read_text(encoding="utf-8")
        self.assertIn('os.getenv("CRASH_REPORT_INCLUDE_SENSITIVE", "0")', source)
        self.assertIn("if CRASH_REPORT_INCLUDE_SENSITIVE else \"[REDACTED]\"", source)

    def test_public_diagnostic_reports_do_not_persist_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "diagnostic.json"
            text_path = Path(tmp) / "diagnostic.txt"
            with (
                mock.patch.object(self.engine, "AUTH_DIAGNOSTIC_JSON_PATH", str(json_path)),
                mock.patch.object(self.engine, "AUTH_DIAGNOSTIC_TXT_PATH", str(text_path)),
            ):
                self.engine.write_auth_diagnostic_report(
                    {
                        "api_key_id": "public-test-key-id",
                        "private" + "_key_path": "C:/example/fixture.pem",
                        "signed_error": "sensitive-response-body",
                    }
                )
            json_text = json_path.read_text(encoding="utf-8")
            text = text_path.read_text(encoding="utf-8")
            combined = json_text + text
            self.assertNotIn("public-test-key-id", combined)
            self.assertNotIn("fixture.pem", combined)
            self.assertNotIn("sensitive-response-body", combined)
            self.assertEqual(json.loads(json_text)["sensitive_fields"], "not_collected")


if __name__ == "__main__":
    unittest.main()
