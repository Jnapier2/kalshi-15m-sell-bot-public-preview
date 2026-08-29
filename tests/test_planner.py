from __future__ import annotations

import unittest

from kalshi_sell_preview.planner import plan_sell


def base_snapshot() -> dict:
    return {
        'schema_version': 'kalshi-sell-public-snapshot-v1',
        'ticker': 'TEST-MARKET-1',
        'market_status': 'open',
        'market_data_age_seconds': 1,
        'status_age_seconds': 2,
        'status_build_id': 'BUILD-1',
        'expected_status_build_id': 'BUILD-1',
        'sell_evidence_complete': True,
        'fee_evidence_complete': True,
        'position_contracts': 25,
        'existing_exit_contracts': 0,
        'projected_net_cents': 2.5,
        'projected_net_per_contract_cents': 0.25,
        'net_to_total_fees_ratio': 2.5,
        'exchange_index': 2,
        'observed_exchange_indexes': [2],
        'route_cache_conflict': False,
    }


class SellPlannerTests(unittest.TestCase):
    def test_eligible_snapshot_emits_fixed_public_plan(self) -> None:
        result = plan_sell(base_snapshot())
        self.assertEqual(result['decision'], 'PLAN')
        self.assertEqual(result['plan']['target_contracts'], '10.00')
        self.assertEqual(result['plan']['target_fraction'], '0.40')
        self.assertEqual(result['plan']['economic_exit_price_cents'], '2')
        self.assertFalse(result['live_write_capability'])

    def test_fee_threshold_defers_without_repricing(self) -> None:
        snapshot = base_snapshot()
        snapshot['projected_net_cents'] = 0.5
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'DEFER')
        self.assertIn('minimum_total_net_not_met', result['reason_codes'])

    def test_shard_conflict_quarantines(self) -> None:
        snapshot = base_snapshot()
        snapshot['observed_exchange_indexes'] = [1, 2]
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'QUARANTINE')
        self.assertIn('conflicting_observed_exchange_indexes', result['reason_codes'])

    def test_stale_status_quarantines(self) -> None:
        snapshot = base_snapshot()
        snapshot['status_age_seconds'] = 31
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'QUARANTINE')
        self.assertIn('sell_status_stale', result['reason_codes'])

    def test_status_build_mismatch_quarantines(self) -> None:
        snapshot = base_snapshot()
        snapshot['status_build_id'] = 'OLD-BUILD'
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'QUARANTINE')
        self.assertIn('sell_status_build_mismatch', result['reason_codes'])

    def test_existing_exit_coverage_holds(self) -> None:
        snapshot = base_snapshot()
        snapshot['existing_exit_contracts'] = 5
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'HOLD')
        self.assertIn('existing_exit_coverage', result['reason_codes'])

    def test_fractional_contract_target_uses_two_decimal_floor(self) -> None:
        snapshot = base_snapshot()
        snapshot['position_contracts'] = '3.33'
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'PLAN')
        self.assertEqual(result['plan']['target_contracts'], '1.33')

    def test_missing_observed_route_evidence_quarantines(self) -> None:
        snapshot = base_snapshot()
        snapshot['observed_exchange_indexes'] = []
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'QUARANTINE')
        self.assertIn('observed_exchange_evidence_missing', result['reason_codes'])

    def test_extreme_position_fails_closed_without_decimal_exception(self) -> None:
        snapshot = base_snapshot()
        snapshot['position_contracts'] = '9999999999999999999999999999'
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'INVALID')
        self.assertIn('position_contracts_out_of_range', result['reason_codes'])

    def test_unknown_critical_input_fails_closed(self) -> None:
        snapshot = base_snapshot()
        snapshot['live'] = True
        result = plan_sell(snapshot)
        self.assertEqual(result['decision'], 'INVALID')
        self.assertIn('unsupported_field:live', result['reason_codes'])


if __name__ == '__main__':
    unittest.main()
