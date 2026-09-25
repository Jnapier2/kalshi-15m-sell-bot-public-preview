"""Public synthetic behavior and exact-package regression tests."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from kalshi_sell_preview.planner import plan

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "run_sell_preview.py"
MODULE = "kalshi_sell_preview"
VERSION = "41.90-public.1"
BUILD = "KALSELL-PUBLIC-41.90.1-COST-REVIEW"
SNAPSHOT = json.loads((ROOT / "examples" / "eligible_exit_snapshot.json").read_text())


def invoke(root=ROOT, *args):
    return subprocess.run([sys.executable, "-I", "-S", "-B", str(root / ENTRY), *args],
                          cwd=tempfile.gettempdir(), capture_output=True, text=True, timeout=10)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.s = copy.deepcopy(SNAPSHOT)

    def changed(self, **fields):
        self.s.update(fields)
        return plan(self.s)

    def test_eligible(self):
        result = plan(self.s)
        self.assertEqual(result["status"], "PLAN")
        self.assertEqual(result["quantity"], 6)
        self.assertEqual(result["price_cents"], 2)
        self.assertEqual(result["mode"], "OFFLINE_ONLY")

    def test_deterministic(self):
        self.assertEqual(plan(self.s), plan(copy.deepcopy(self.s)))

    def test_duplicate(self):
        self.s["seen_intent_ids"] = [plan(self.s)["intent_id"]]
        self.assertEqual(plan(self.s)["reason"], "DUPLICATE_INTENT")

    def test_scope_changes_identity(self):
        first = plan(self.s)["intent_id"]
        result = self.changed(scope="SYNTHETIC-SCOPE-B", observed_scope="SYNTHETIC-SCOPE-B")
        self.assertNotEqual(first, result["intent_id"])

    def test_scope_conflict(self):
        self.assertEqual(self.changed(observed_scope="SYNTHETIC-SCOPE-B")["status"], "QUARANTINE")

    def test_route_conflict(self):
        self.assertEqual(self.changed(observed_route="SYNTHETIC-ROUTE-B")["status"], "QUARANTINE")

    def test_status_identity(self):
        self.assertEqual(self.changed(status_build="OLD")["reason"], "STATUS_IDENTITY_CONFLICT")

    def test_ambiguous_prior_intent(self):
        self.assertEqual(self.changed(prior_intent_ambiguous=True)["reason"], "RECONCILIATION_REQUIRED")

    def test_stale_market(self):
        self.assertEqual(self.changed(age_seconds=31)["reason"], "STALE_EVIDENCE")

    def test_stale_status(self):
        self.assertEqual(self.changed(status_age_seconds=31)["reason"], "STALE_EVIDENCE")

    def test_stale_fees(self):
        self.assertEqual(self.changed(fee_age_seconds=31)["reason"], "STALE_EVIDENCE")

    def test_age_boundary(self):
        self.assertEqual(self.changed(age_seconds=30, status_age_seconds=30, fee_age_seconds=30)["status"], "PLAN")

    def test_missing_evidence(self):
        self.assertEqual(self.changed(evidence_complete=False)["status"], "HOLD")

    def test_missing_fees(self):
        self.assertEqual(self.changed(fees_complete=False)["status"], "HOLD")

    def test_closed_market(self):
        self.assertEqual(self.changed(market_open=False)["status"], "HOLD")

    def test_exchange_unavailable(self):
        self.assertEqual(self.changed(exchange_ready=False)["status"], "HOLD")

    def test_synthetic_required(self):
        self.assertEqual(self.changed(synthetic=False)["status"], "INVALID")

    def test_production_identifier_rejected(self):
        self.assertEqual(self.changed(market="NOT-A-SYNTHETIC-ID")["status"], "INVALID")

    def test_unknown_fields(self):
        self.assertEqual(self.changed(extra="DO_NOT_ECHO_SENTINEL")["status"], "INVALID")
        self.assertNotIn("DO_NOT_ECHO_SENTINEL", json.dumps(plan(self.s)))

    def test_missing_field(self):
        del self.s["fee_age_seconds"]
        self.assertEqual(plan(self.s)["status"], "INVALID")

    def test_bounded_integer(self):
        for value in [-1, 1.5, True, "1", None, 1000001, float("nan")]:
            with self.subTest(value=repr(value)):
                self.assertEqual(self.changed(age_seconds=value)["status"], "INVALID")

    def test_exact_boolean(self):
        self.assertEqual(self.changed(fees_complete=1)["status"], "INVALID")

    def test_invalid_side(self):
        self.assertEqual(self.changed(side="other")["status"], "INVALID")

    def test_malformed_prior_ids(self):
        self.assertEqual(self.changed(seen_intent_ids=["not-an-id"])["status"], "INVALID")

    def test_bounded_prior_ids(self):
        self.assertEqual(self.changed(seen_intent_ids=["0" * 64] * 101)["status"], "INVALID")

    def test_no_input_mutation(self):
        before = copy.deepcopy(self.s)
        plan(self.s)
        self.assertEqual(self.s, before)

    def test_socket_tripwire(self):
        with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")):
            self.assertEqual(plan(self.s)["status"], "PLAN")

    def test_sixty_percent_not_legacy_forty(self):
        self.assertEqual(plan(self.s)["target_contracts"], 6)
        self.assertEqual(plan(self.s)["target_fraction"], "0.60")

    def test_reserved_coverage(self):
        self.assertEqual(self.changed(reserved_exit_contracts=6)["reason"], "TARGET_ALREADY_COVERED")

    def test_fills_alone_do_not_increase_target(self):
        result = self.changed(confirmed_exit_contracts=2, position_contracts=8, entry_fee_cents=0, exit_fee_cents=0)
        self.assertEqual(result["target_contracts"], 6)
        self.assertEqual(result["quantity"], 4)

    def test_new_acquisitions_raise_target(self):
        result = self.changed(verified_acquired_contracts=20, position_contracts=20)
        self.assertEqual(result["target_contracts"], 12)

    def test_reservations_reduce_candidate(self):
        result = self.changed(reserved_exit_contracts=2, entry_fee_cents=0, exit_fee_cents=0)
        self.assertEqual(result["quantity"], 4)

    def test_position_conflict(self):
        self.assertEqual(self.changed(position_contracts=11)["status"], "QUARANTINE")

    def test_over_reserved(self):
        self.assertEqual(self.changed(reserved_exit_contracts=11)["status"], "QUARANTINE")

    def test_fee_defer(self):
        result = self.changed(entry_fee_cents=3, exit_fee_cents=3)
        self.assertEqual(result["status"], "DEFER")
        self.assertEqual(result["target_contracts"], 6)

    def test_fee_ratio_boundary(self):
        result = plan(self.s)
        self.assertEqual(result["modeled_net_cents"], 4)
        self.assertEqual(result["modeled_total_fee_cents"], 2)

    def test_whole_contract_floor(self):
        result = self.changed(verified_acquired_contracts=11, position_contracts=11)
        self.assertEqual(result["quantity"], 6)

    def test_zero_position(self):
        result = self.changed(verified_acquired_contracts=0, position_contracts=0)
        self.assertEqual(result["status"], "HOLD")

    def test_fractional_contract_rejected(self):
        self.assertEqual(self.changed(verified_acquired_contracts=10.5)["status"], "INVALID")


class PackageTests(unittest.TestCase):
    def clone(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        target = Path(temp.name) / "copy with spaces"
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "outputs", "__pycache__"))
        return target

    def test_complete_manifest(self):
        result = invoke(ROOT, "--verify")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_demo_from_unrelated_directory(self):
        result = invoke(ROOT, "--demo")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PLAN")

    def test_relative_input_is_project_local(self):
        result = invoke(ROOT, "examples/conflict_snapshot.json")
        self.assertEqual(json.loads(result.stdout)["status"], "QUARANTINE")

    def test_unsafe_startup_flags_denied(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / ENTRY), "--demo"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("-I -S -B", result.stdout)

    def test_menu_eof_exits(self):
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(ROOT / ENTRY), "--menu"],
                                input="", capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)

    def test_unsupported_live_flag(self):
        result = invoke(ROOT, "--live")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "UNSUPPORTED_ARGUMENT")

    def test_payload_tamper_fails_and_exports(self):
        root = self.clone()
        with (root / MODULE / "planner.py").open("a") as stream:
            stream.write("\n# modified\n")
        result = invoke(root, "--demo")
        self.assertEqual(result.returncode, 2)
        self.assertIn("PACKAGE_INTEGRITY_FAILURE", result.stdout)
        archives = list((root / "outputs" / "support").glob("*.zip"))
        self.assertEqual(len(archives), 1)
        with zipfile.ZipFile(archives[0]) as archive:
            self.assertEqual(len(archive.namelist()), 4)
            self.assertEqual(json.loads(archive.read("identity.json"))["integrity"], "FAIL")

    def test_extra_payload_blocks(self):
        root = self.clone()
        (root / "unexpected.txt").write_text("DO_NOT_EXPORT_SENTINEL")
        result = invoke(root, "--demo")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("DO_NOT_EXPORT_SENTINEL", result.stdout)

    def test_missing_payload_blocks(self):
        root = self.clone()
        (root / MODULE / "planner.py").unlink()
        self.assertEqual(invoke(root, "--demo").returncode, 2)

    def test_corrupt_manifest_blocks(self):
        root = self.clone()
        (root / "MANIFEST.json").write_text("{}")
        self.assertEqual(invoke(root, "--demo").returncode, 2)

    def test_export_independent_of_manifest_and_planner(self):
        root = self.clone()
        (root / "MANIFEST.json").unlink()
        (root / MODULE / "planner.py").unlink()
        (root / "private_input.txt").write_text("DO_NOT_EXPORT_SENTINEL")
        result = invoke(root, "--export")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = root / json.loads(result.stdout)["path"]
        self.assertTrue(path.is_relative_to(root / "outputs" / "support"))
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(len(archive.namelist()), 4)
            for name in archive.namelist():
                self.assertNotIn(b"DO_NOT_EXPORT_SENTINEL", archive.read(name))
                self.assertNotIn(str(root).encode(), archive.read(name))

    def test_export_error_is_bounded(self):
        root = self.clone()
        (root / "outputs").write_text("blocked output")
        result = invoke(root, "--export")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["code"], "EXPORT_FAILED")

    def test_strict_json_loader(self):
        root = self.clone()
        (root / "outputs").mkdir()
        path = root / "outputs" / "sample.json"
        for text in ['{"x":1,"x":2}', '{"x":NaN}', ' ' * 65537, '{broken']:
            with self.subTest(text=text[:20]):
                path.write_text(text)
                result = invoke(root, str(path))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["reason"], "INPUT_REJECTED")

    def test_metadata_and_notice(self):
        m = json.loads((ROOT / "PACKAGE_METADATA.json").read_text())
        self.assertEqual(m["display_version"], VERSION)
        self.assertEqual(m["build_id"], BUILD)
        for field in ["network_access", "credential_support", "live_write_capability"]:
            self.assertIs(m[field], False)
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())
        self.assertIn("Gateway Information Group LLC", (ROOT / "README.md").read_text())

    def test_launchers_preserve_local_root_and_isolation(self):
        launchers = sorted(path.name for path in ROOT.glob("*.bat"))
        self.assertEqual(launchers, sorted(["Kalshi15mSellPreview.bat", "Kalshi15mSellPreview_Export.bat"]))
        for name in launchers:
            text = (ROOT / name).read_text()
            self.assertIn('pushd "%~dp0"', text)
            self.assertIn("-I -S -B", text)
            self.assertNotIn("ExecutionPolicy", text)
        self.assertIn("--export", (ROOT / "Kalshi15mSellPreview_Export.bat").read_text())

    def test_runtime_import_allowlist(self):
        allowed = {"sys", "hashlib", "json", "os", "pathlib", "re", "uuid", "runpy", "stat", MODULE}
        for path in [ROOT / ENTRY, *sorted((ROOT / MODULE).glob("*.py"))]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [item.name.split(".")[0] for item in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "").split(".")[0]]
                else:
                    continue
                for name in names:
                    self.assertIn(name, allowed, str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__"})

    def test_no_private_payload_names(self):
        manifest = json.loads((ROOT / "MANIFEST.json").read_text())
        for name in manifest["files"]:
            self.assertFalse(name.endswith((".pem", ".key", ".zip", ".log")))
            self.assertFalse(Path(name).name.startswith(".env"))
        self.assertEqual(len(manifest["files"]) + 1, 29)

    def test_all_examples_valid_and_synthetic(self):
        for path in (ROOT / "examples").glob("*.json"):
            value = json.loads(path.read_text())
            self.assertIs(value["synthetic"], True)
            self.assertNotEqual(plan(value)["status"], "INVALID")

    def test_source_parses(self):
        for path in ROOT.rglob("*.py"):
            if "outputs" not in path.relative_to(ROOT).parts:
                ast.parse(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
