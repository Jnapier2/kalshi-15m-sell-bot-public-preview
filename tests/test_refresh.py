"""Regression tests for synthetic evidence and bounded, independent support."""
import ast
import copy
import io
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
ENTRY = 'run_sell_preview.py'
SAMPLE = json.loads((ROOT / 'examples' / 'eligible_exit_snapshot.json').read_text())


class RefreshPackageTests(unittest.TestCase):
    def clone(self):
        # Tests own their temporary roots under project outputs; nothing private copied.
        folder = ROOT / 'outputs' / 'tests'
        folder.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=folder)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / 'project & spaces'
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', 'outputs', '__pycache__'))
        return root

    def invoke(self, root, entry, *args):
        return subprocess.run([sys.executable, '-I', '-S', '-B', str(root / entry), *args],
                              capture_output=True, text=True, timeout=10, cwd=root.parent)

    def test_export_when_main_disabled(self):
        root = self.clone()
        (root / ENTRY).unlink()
        (root / 'MANIFEST.json').unlink()
        (root / 'PACKAGE_METADATA.json').unlink()
        shutil.rmtree(root / 'kalshi_sell_preview')
        result = self.invoke(root, 'public_support.py', '--export')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['file_count'], 4)
        with zipfile.ZipFile(root / payload['path']) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(json.loads(archive.read('diagnostics.json'))['application_health'], 'NOT_CHECKED')

    def test_tampered_exporter_never_runs(self):
        root = self.clone()
        (root / 'public_support.py').write_text('raise RuntimeError("UNTRUSTED_SENTINEL")')
        result = self.invoke(root, ENTRY, '--export')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('UNTRUSTED_SENTINEL', result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['code'], 'SUPPORT_UNAVAILABLE')

    def test_critical_capsule_precedes_zip(self):
        root = self.clone()
        (root / 'VERSION.txt').write_text('changed')
        result = self.invoke(root, ENTRY, '--demo')
        self.assertEqual(result.returncode, 2)
        folder = root / 'outputs' / 'support'
        self.assertEqual(len(list(folder.glob('Critical_*.json'))), 1)
        self.assertEqual(len(list(folder.glob('Export20_*.zip'))), 1)
        self.assertEqual(list(folder.glob('.stage-*')), [])

    def test_invalid_input_is_not_critical(self):
        root = self.clone()
        result = self.invoke(root, ENTRY, 'missing.json')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((root / 'outputs' / 'support').exists())

    def test_export_lock_preserved_on_contention(self):
        root = self.clone()
        folder = root / 'outputs' / 'support'
        folder.mkdir(parents=True)
        lock = folder / '.export.lock'
        lock.write_text('sentinel')
        result = self.invoke(root, 'public_support.py', '--export')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(lock.read_text(), 'sentinel')

    def test_budget_does_not_prune_evidence(self):
        root = self.clone()
        folder = root / 'outputs' / 'support'
        folder.mkdir(parents=True)
        (folder / '.export_count').write_text('64')
        (folder / 'protected.txt').write_text('protected')
        result = self.invoke(root, 'public_support.py', '--export')
        self.assertEqual(result.returncode, 2)
        self.assertEqual((folder / 'protected.txt').read_text(), 'protected')
        self.assertEqual(list(folder.glob('*.zip')), [])

    def test_symlink_input_rejected(self):
        root = self.clone()
        folder = root / 'outputs'
        folder.mkdir()
        target = folder / 'target.json'
        target.write_text(json.dumps(SAMPLE))
        link = folder / 'link.json'
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest('Host does not permit symlink creation: ' + type(exc).__name__)
        result = self.invoke(root, ENTRY, str(link))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['reason'], 'INPUT_REJECTED')

    def test_output_symlink_rejected_without_external_writes(self):
        root = self.clone()
        external = root.parent / 'outside'
        external.mkdir()
        try:
            (root / 'outputs').symlink_to(external, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Host does not permit symlink creation: ' + type(exc).__name__)
        result = self.invoke(root, 'public_support.py', '--export')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(external.iterdir()), [])

    def test_atomic_archive_not_visible_during_compression(self):
        root = self.clone()
        module = runpy.run_path(str(root / 'public_support.py'))
        observed = []
        original = zipfile.ZipFile.writestr
        def wrapped(archive, *args, **kwargs):
            observed.append(list((root / 'outputs' / 'support').glob('*.zip')))
            return original(archive, *args, **kwargs)
        with patch('zipfile.ZipFile.writestr', wrapped):
            result = module['export_support']()
        self.assertEqual(result['status'], 'EXPORTED')
        self.assertEqual(observed, [[], [], [], []])

    def test_same_run_critical_deduplicated(self):
        root = self.clone()
        export = runpy.run_path(str(root / 'public_support.py'))['export_support']
        first = export('FAIL')
        second = export('FAIL')
        self.assertEqual(first['status'], 'EXPORTED')
        self.assertEqual(second['status'], 'SUPPRESSED')
        self.assertEqual(len(list((root / 'outputs/support').glob('*.zip'))), 1)

    def test_low_disk_has_no_fallback(self):
        root = self.clone()
        export = runpy.run_path(str(root / 'public_support.py'))['export_support']
        usage = type('Usage', (), {'free': 0})()
        with patch('shutil.disk_usage', return_value=usage):
            result = export()
        self.assertEqual(result['status'], 'ERROR')
        self.assertFalse(list(root.rglob('*.zip')))

    def test_partial_capture_has_distinct_status(self):
        root = self.clone()
        export = runpy.run_path(str(root / 'public_support.py'))['export_support']
        with patch('zipfile.ZipFile', side_effect=OSError('DO_NOT_ECHO')):
            result = export('FAIL')
        self.assertEqual(result['status'], 'CAPSULE_ONLY')
        self.assertTrue((root / result['path']).is_file())
        self.assertNotIn('DO_NOT_ECHO', json.dumps(result))

    def test_support_runtime_imports_allowlist(self):
        allowed = {'sys', 'hashlib', 'io', 'json', 'os', 'pathlib', 'shutil', 'stat', 'time', 'uuid', 'zipfile'}
        tree = ast.parse((ROOT / 'public_support.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split('.')[0], allowed)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module.split('.')[0], allowed)

    def test_export_uses_no_input_values(self):
        root = self.clone()
        (root / 'private.txt').write_text('DO_NOT_EXPORT_PRIVATE_SENTINEL')
        result = self.invoke(root, 'public_support.py', '--export')
        with zipfile.ZipFile(root / json.loads(result.stdout)['path']) as archive:
            self.assertNotIn(b'DO_NOT_EXPORT_PRIVATE_SENTINEL', b''.join(archive.read(n) for n in archive.namelist()))


MODEL = {
    'proof_complete': True, 'packet_cost_units': 100, 'packet_entry_fee_units': 100,
    'ticks': [{'price_units': p, 'maker_fee_units': 100, 'taker_fee_units': 100} for p in [50, 100, 150, 200]],
    'bids': [], 'book_age_seconds': 1, 'passive_allowed': True,
    'competing_ask_units': 200, 'own_quote_units': None, 'seconds_to_close': 300
}


class CostReviewTests(unittest.TestCase):
    def sample(self):
        sample = copy.deepcopy(SAMPLE)
        del sample['entry_fee_cents']
        del sample['exit_fee_cents']
        sample['cost_model'] = copy.deepcopy(MODEL)
        return sample

    def test_competitive_price_and_full_packet_arithmetic(self):
        result = plan(self.sample())
        self.assertEqual(result['status'], 'PLAN')
        self.assertEqual(result['price_units'], 150)
        self.assertEqual(result['modeled_net_units'], 6 * 150 - 100 - 100 - 100)
        self.assertEqual(result['quantity'], 6)
        self.assertIs(result['expected_fill'], False)

    def test_mixed_fee_units_rejected(self):
        sample = self.sample()
        sample['entry_fee_cents'] = 1
        self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_incomplete_proof_blocks(self):
        sample = self.sample()
        sample['cost_model']['proof_complete'] = False
        self.assertEqual(plan(sample)['reason'], 'COST_PROOF_INCOMPLETE')

    def test_highest_qualifying_depth(self):
        sample = self.sample()
        sample['cost_model']['bids'] = [{'price_units': 200, 'quantity': 6}]
        self.assertEqual(plan(sample)['price_units'], 200)

    def test_stale_depth_cannot_authorize_quote(self):
        sample = self.sample()
        sample['cost_model'].update(bids=[{'price_units': 200, 'quantity': 6}], book_age_seconds=3, passive_allowed=False)
        self.assertEqual(plan(sample)['status'], 'HOLD')

    def test_passive_not_a_fill_claim(self):
        sample = self.sample()
        sample['cost_model'].update(book_age_seconds=3, competing_ask_units=None)
        result = plan(sample)
        self.assertEqual(result['pricing_basis'], 'COST_FLOOR_LIMIT_LIQUIDITY_UNKNOWN')
        self.assertIs(result['expected_fill'], False)

    def test_no_passive_without_depth(self):
        sample = self.sample()
        sample['cost_model']['passive_allowed'] = False
        self.assertEqual(plan(sample)['status'], 'HOLD')

    def test_bad_tick_in_middle_is_not_assumed_safe(self):
        sample = self.sample()
        sample['cost_model']['ticks'][2]['taker_fee_units'] = 1000
        result = plan(sample)
        self.assertEqual(result['price_units'], 200)

    def test_maker_and_taker_both_checked(self):
        sample = self.sample()
        sample['cost_model']['ticks'][2]['maker_fee_units'] = 1000
        self.assertEqual(plan(sample)['price_units'], 200)

    def test_no_safe_price_defers(self):
        sample = self.sample()
        sample['cost_model']['packet_cost_units'] = 10000
        self.assertEqual(plan(sample)['reason'], 'NO_COST_SAFE_TICK')

    def test_own_quote_preserved_without_competitor(self):
        sample = self.sample()
        sample['cost_model'].update(competing_ask_units=None, own_quote_units=200)
        self.assertEqual(plan(sample)['price_units'], 200)

    def test_close_window_selects_cost_floor(self):
        sample = self.sample()
        sample['cost_model'].update(own_quote_units=200, competing_ask_units=None, seconds_to_close=120)
        self.assertEqual(plan(sample)['price_units'], 150)

    def test_zero_close_time_holds(self):
        sample = self.sample()
        sample['cost_model']['seconds_to_close'] = 0
        self.assertEqual(plan(sample)['status'], 'HOLD')

    def test_after_fill_not_adaptively_repriced(self):
        sample = self.sample()
        sample.update(confirmed_exit_contracts=1, position_contracts=9)
        self.assertEqual(plan(sample)['reason'], 'ADAPTIVE_AFTER_FILL_DEFERRED')

    def test_bad_duplicate_ticks_rejected(self):
        sample = self.sample()
        sample['cost_model']['ticks'].append(copy.deepcopy(sample['cost_model']['ticks'][0]))
        self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_bad_duplicate_depth_rejected(self):
        sample = self.sample()
        sample['cost_model']['bids'] = [{'price_units': 200, 'quantity': 3}] * 2
        self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_out_of_ceiling_tick_rejected(self):
        sample = self.sample()
        sample['cost_model']['ticks'][0]['price_units'] = 201
        self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_missing_fee_rejected(self):
        sample = self.sample()
        del sample['cost_model']['ticks'][0]['taker_fee_units']
        self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_noninteger_values_rejected(self):
        for value in [None, True, -1, 1.5, '100', 100000001]:
            with self.subTest(value=value):
                sample = self.sample()
                sample['cost_model']['packet_cost_units'] = value
                self.assertEqual(plan(sample)['status'], 'INVALID')

    def test_lower_price_changes_intent(self):
        sample = self.sample()
        first = plan(sample)['intent_id']
        sample['cost_model']['bids'] = [{'price_units': 200, 'quantity': 6}]
        self.assertNotEqual(plan(sample)['intent_id'], first)

    def test_cost_plan_duplicate_rejected(self):
        sample = self.sample()
        sample['seen_intent_ids'] = [plan(sample)['intent_id']]
        self.assertEqual(plan(sample)['reason'], 'DUPLICATE_INTENT')

    def test_all_prices_match_independent_floor(self):
        # Exhaustive finite scenarios use independent integer comparisons, not helper output.
        for cost in [0, 100, 700, 1500]:
            sample = self.sample()
            sample['cost_model'].update(packet_cost_units=cost, seconds_to_close=120)
            valid = [p for p in [50, 100, 150, 200] if 6*p-cost-200 >= max(100, 60, 400)]
            result = plan(sample)
            if valid:
                self.assertEqual(result['price_units'], min(valid))
            else:
                self.assertEqual(result['status'], 'DEFER')


if __name__ == '__main__':
    unittest.main()
