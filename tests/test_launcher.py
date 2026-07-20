from __future__ import annotations

import argparse
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import bot
from public_safety import DEMO_BASE_URL


class LauncherTests(unittest.TestCase):
    def config(self, environment="demo"):
        return {
            "schema_version": 1,
            "environment": environment,
            "api_key_id": "sample-key-id-1234",
            "private_key_path": str(Path(tempfile.gettempdir()) / "outside-project.key"),
            "instance_name": "TEST",
        }

    def test_dry_child_environment_strips_proxy_and_python_injection(self):
        injected = {
            "HTTPS_PROXY": "http://proxy.invalid",
            "http_proxy": "http://proxy.invalid",
            "PYTHONPATH": "/tmp/inject",  # nosec B108
            "KALSHI_BASE_URL": "https://example.invalid",
            "DRY_RUN": "0",
            "FORCE_LIVE_RUN": "1",
            "LIVE_TRADING_ACK": "anything",
        }
        with mock.patch.dict(os.environ, injected, clear=False):
            env = bot._child_environment(self.config(), dry_run=True, run_once=True)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("http_proxy", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["KALSHI_BASE_URL"], DEMO_BASE_URL)
        self.assertEqual(env["DRY_RUN"], "1")
        self.assertEqual(env["FORCE_LIVE_RUN"], "0")
        self.assertNotIn("LIVE_TRADING_ACK", env)
        self.assertEqual(env["RUN_ONCE"], "1")

    def test_child_environment_refuses_order_capable_mode(self):
        with self.assertRaisesRegex(RuntimeError, "10x1c flagship"):
            bot._child_environment(self.config("production"), dry_run=False, run_once=False)

    def test_runtime_directories_are_outside_repository(self):
        env = bot._child_environment(self.config(), dry_run=True, run_once=True)
        root = bot.PROJECT_ROOT.resolve()
        for key in ("BOT_DATA_DIR", "BOT_EXPORT_DIR"):
            with self.assertRaises(ValueError):
                Path(env[key]).resolve().relative_to(root)

    def test_live_command_returns_positive_flagship_guidance(self):
        with redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "10x1c flagship"):
                bot.cmd_live(argparse.Namespace())

    def test_live_command_never_loads_credentials(self):
        with mock.patch.object(bot, "_validated_config") as load_config, redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                bot.cmd_live(argparse.Namespace())
        load_config.assert_not_called()

    def test_live_command_never_launches_engine(self):
        with mock.patch.object(bot, "_run_engine") as run_engine, redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                bot.cmd_live(argparse.Namespace())
        run_engine.assert_not_called()

    def test_live_parser_rejects_removed_ack_bypass(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            bot.build_parser().parse_args(["live", "--ack", "anything"])

    def test_run_defaults_to_dry_run(self):
        args = argparse.Namespace(live=False, production=False, continuous=False)
        with mock.patch.object(bot, "cmd_dry_run", return_value=17) as dry, mock.patch.object(bot, "cmd_live") as live:
            self.assertEqual(bot.cmd_run(args), 17)
        dry.assert_called_once()
        live.assert_not_called()

    def test_run_live_is_blocked_with_no_dry_run_fallback(self):
        args = argparse.Namespace(live=True, production=False, continuous=True)
        with mock.patch.object(bot, "cmd_dry_run") as dry, redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "10x1c flagship"):
                bot.cmd_run(args)
        dry.assert_not_called()

    def test_run_production_flag_requires_live(self):
        args = argparse.Namespace(live=False, production=True, continuous=False)
        with self.assertRaises(RuntimeError):
            bot.cmd_run(args)

    def test_run_parser_is_dry_by_default(self):
        args = bot.build_parser().parse_args(["run"])
        self.assertFalse(args.live)
        self.assertFalse(args.production)
        self.assertFalse(args.continuous)
        self.assertFalse(hasattr(args, "ack"))
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            bot.build_parser().parse_args(["run", "--ack", "anything"])

    def test_status_keeps_identifier_private(self):
        with mock.patch.object(bot, "_load_config", return_value=self.config()):
            stream = io.StringIO()
            with redirect_stdout(stream):
                bot.cmd_status(argparse.Namespace())
        output = stream.getvalue()
        self.assertNotIn("sample-key-id-1234", output)
        self.assertIn("stored privately", output)

    def test_parser_defaults_to_no_command(self):
        args = bot.build_parser().parse_args([])
        self.assertIsNone(args.command)


if __name__ == "__main__":
    unittest.main()
