from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA_VERSION = 'kalshi-sell-public-snapshot-v1'
TARGET_FRACTION = Decimal('0.40')
ECONOMIC_EXIT_PRICE_CENTS = Decimal('2')
MIN_NET_CENTS = Decimal('1.00')
MIN_NET_PER_CONTRACT_CENTS = Decimal('0.10')
MIN_NET_TO_TOTAL_FEES_RATIO = Decimal('2.00')
MAX_MARKET_DATA_AGE_SECONDS = Decimal('10')
MAX_STATUS_AGE_SECONDS = Decimal('30')
MAX_POSITION_CONTRACTS = Decimal('1000000000')
MAX_EVIDENCE_MAGNITUDE = Decimal('1000000000000')
TICKER_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9_.:-]{2,63}$')
ALLOWED_FIELDS = {
    'schema_version', 'ticker', 'market_status', 'market_data_age_seconds',
    'status_age_seconds', 'status_build_id', 'expected_status_build_id',
    'sell_evidence_complete', 'fee_evidence_complete', 'position_contracts',
    'existing_exit_contracts', 'projected_net_cents',
    'projected_net_per_contract_cents', 'net_to_total_fees_ratio',
    'exchange_index', 'observed_exchange_indexes', 'route_cache_conflict',
    'notes',
}


def _decimal(value: Any, field: str, errors: list[str]) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(f'invalid_{field}')
        return Decimal('0')
    if not result.is_finite():
        errors.append(f'invalid_{field}')
        return Decimal('0')
    return result


def _plan_id(snapshot: Mapping[str, Any], target_contracts: Decimal) -> str:
    body = {
        'ticker': snapshot.get('ticker'),
        'status_build_id': snapshot.get('status_build_id'),
        'exchange_index': snapshot.get('exchange_index'),
        'target_contracts': str(target_contracts),
        'economic_exit_price_cents': str(ECONOMIC_EXIT_PRICE_CENTS),
    }
    encoded = json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return 'public-exit-' + hashlib.sha256(encoded).hexdigest()[:24]


def plan_sell(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    holds: list[str] = []
    defers: list[str] = []
    quarantines: list[str] = []

    if not isinstance(snapshot, Mapping):
        return _result('INVALID', ['snapshot_not_object'], None)

    unknown = sorted(set(snapshot) - ALLOWED_FIELDS)
    if unknown:
        errors.extend(f'unsupported_field:{name}' for name in unknown)
    if snapshot.get('schema_version') != SCHEMA_VERSION:
        errors.append('unsupported_schema_version')

    ticker = snapshot.get('ticker')
    if not isinstance(ticker, str) or not TICKER_PATTERN.fullmatch(ticker):
        errors.append('invalid_ticker')
    if snapshot.get('market_status') != 'open':
        holds.append('market_not_open')

    market_age = _decimal(snapshot.get('market_data_age_seconds'), 'market_data_age_seconds', errors)
    status_age = _decimal(snapshot.get('status_age_seconds'), 'status_age_seconds', errors)
    if market_age < 0 or market_age > MAX_MARKET_DATA_AGE_SECONDS:
        quarantines.append('market_data_stale')
    if status_age < 0 or status_age > MAX_STATUS_AGE_SECONDS:
        quarantines.append('sell_status_stale')

    status_build = snapshot.get('status_build_id')
    expected_build = snapshot.get('expected_status_build_id')
    if not isinstance(status_build, str) or not status_build:
        errors.append('invalid_status_build_id')
    if not isinstance(expected_build, str) or not expected_build:
        errors.append('invalid_expected_status_build_id')
    if status_build and expected_build and status_build != expected_build:
        quarantines.append('sell_status_build_mismatch')

    if snapshot.get('sell_evidence_complete') is not True:
        quarantines.append('sell_evidence_incomplete')
    if snapshot.get('fee_evidence_complete') is not True:
        defers.append('fee_evidence_incomplete')

    position = _decimal(snapshot.get('position_contracts'), 'position_contracts', errors)
    existing_exit = _decimal(snapshot.get('existing_exit_contracts'), 'existing_exit_contracts', errors)
    if position < 0 or existing_exit < 0:
        errors.append('negative_contract_value')
    if position > MAX_POSITION_CONTRACTS:
        errors.append('position_contracts_out_of_range')
    if existing_exit > MAX_POSITION_CONTRACTS:
        errors.append('existing_exit_contracts_out_of_range')
    eligible = max(position - existing_exit, Decimal('0'))
    try:
        target_contracts = (eligible * TARGET_FRACTION).quantize(Decimal('0.01'), rounding=ROUND_FLOOR)
    except InvalidOperation:
        errors.append('target_quantization_failed')
        target_contracts = Decimal('0')
    if position == 0:
        holds.append('no_sell_position')
    if existing_exit > 0:
        holds.append('existing_exit_coverage')
    if target_contracts < Decimal('0.01'):
        holds.append('target_rounds_to_zero')

    projected_net = _decimal(snapshot.get('projected_net_cents'), 'projected_net_cents', errors)
    projected_per_contract = _decimal(
        snapshot.get('projected_net_per_contract_cents'),
        'projected_net_per_contract_cents',
        errors,
    )
    fee_ratio = _decimal(snapshot.get('net_to_total_fees_ratio'), 'net_to_total_fees_ratio', errors)
    if any(abs(value) > MAX_EVIDENCE_MAGNITUDE for value in (projected_net, projected_per_contract, fee_ratio)):
        errors.append('financial_evidence_out_of_range')
    if projected_net < MIN_NET_CENTS:
        defers.append('minimum_total_net_not_met')
    if projected_per_contract < MIN_NET_PER_CONTRACT_CENTS:
        defers.append('minimum_net_per_contract_not_met')
    if fee_ratio < MIN_NET_TO_TOTAL_FEES_RATIO:
        defers.append('minimum_fee_ratio_not_met')

    exchange_index = snapshot.get('exchange_index')
    if not isinstance(exchange_index, int) or isinstance(exchange_index, bool) or exchange_index < -1:
        errors.append('invalid_exchange_index')

    observed = snapshot.get('observed_exchange_indexes')
    if not isinstance(observed, list) or any(
        not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in observed
    ):
        errors.append('invalid_observed_exchange_indexes')
        observed_set: set[int] = set()
    else:
        observed_set = set(observed)
        if not observed_set:
            quarantines.append('observed_exchange_evidence_missing')
        if len(observed_set) > 1:
            quarantines.append('conflicting_observed_exchange_indexes')
        if isinstance(exchange_index, int) and exchange_index >= 0 and observed_set and exchange_index not in observed_set:
            quarantines.append('intended_observed_shard_mismatch')
    if snapshot.get('route_cache_conflict') is not False:
        quarantines.append('route_cache_conflict')

    plan_id = _plan_id(snapshot, target_contracts) if not errors else None
    if errors:
        return _result('INVALID', errors, plan_id)
    if quarantines:
        return _result('QUARANTINE', quarantines, plan_id)
    if holds:
        return _result('HOLD', holds, plan_id)
    if defers:
        return _result('DEFER', defers, plan_id)

    route_mode = 'direct' if exchange_index >= 0 else 'auto'
    return {
        **_result('PLAN', [], plan_id),
        'plan': {
            'ticker': ticker,
            'target_contracts': str(target_contracts),
            'target_fraction': str(TARGET_FRACTION),
            'economic_exit_price_cents': str(ECONOMIC_EXIT_PRICE_CENTS),
            'route_mode': route_mode,
            'exchange_index': exchange_index,
            'projected_net_cents': str(projected_net),
            'projected_net_per_contract_cents': str(projected_per_contract),
            'net_to_total_fees_ratio': str(fee_ratio),
        },
    }


def _result(decision: str, reasons: list[str], plan_id: str | None) -> dict[str, Any]:
    return {
        'schema_version': 'kalshi-sell-public-plan-result-v1',
        'decision': decision,
        'reason_codes': sorted(set(reasons)),
        'plan_id': plan_id,
        'network_access': False,
        'credential_support': False,
        'live_write_capability': False,
        'write_authority': 'none',
    }
