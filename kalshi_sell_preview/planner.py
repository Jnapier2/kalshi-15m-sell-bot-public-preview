"""Deterministic synthetic-data planner. No transport or credential surface."""
import hashlib
import json
import re

BUILD = "KALSELL-PUBLIC-41.84.1-OFFLINE-REPLACEMENT"
SCHEMA = "kalshi-public-snapshot-v2"
TEXT_FIELDS = {"market", "round", "scope", "observed_scope", "route", "observed_route"}
BOOL_FIELDS = {"synthetic", "market_open", "exchange_ready", "evidence_complete", "fees_complete", "prior_intent_ambiguous"}
COMMON_FIELDS = TEXT_FIELDS | BOOL_FIELDS | {"schema", "side", "status_build", "age_seconds", "status_age_seconds", "fee_age_seconds", "seen_intent_ids"}
INTEGER_FIELDS = ['verified_acquired_contracts', 'confirmed_exit_contracts', 'position_contracts', 'reserved_exit_contracts', 'entry_fee_cents', 'exit_fee_cents']
EXTRA_BOOLS = []
REQUIRED = COMMON_FIELDS | set(INTEGER_FIELDS) | set(EXTRA_BOOLS)


def outcome(status, reason, **details):
    return {"status": status, "reason": reason, "mode": "OFFLINE_ONLY", "synthetic": True, **details}


def plan(snapshot):
    """Fail closed; input quantities and fees are invented evidence, never live data."""
    if not isinstance(snapshot, dict) or set(snapshot) != REQUIRED:
        return outcome("INVALID", "SCHEMA_MISMATCH")
    s = snapshot
    if s["schema"] != SCHEMA or s["synthetic"] is not True or s["side"] not in ("yes", "no"):
        return outcome("INVALID", "SYNTHETIC_INPUT_REQUIRED")
    for key in TEXT_FIELDS:
        if not isinstance(s[key], str) or not re.fullmatch(r"SYNTHETIC-[A-Z0-9_-]{1,40}", s[key]):
            return outcome("INVALID", "SYNTHETIC_IDENTIFIER_REQUIRED")
    if any(type(s[key]) is not bool for key in BOOL_FIELDS | set(EXTRA_BOOLS)):
        return outcome("INVALID", "BOOLEAN_REQUIRED")
    for key in ("age_seconds", "status_age_seconds", "fee_age_seconds", *INTEGER_FIELDS):
        if type(s[key]) is not int or not 0 <= s[key] <= 1000000:
            return outcome("INVALID", "BOUNDED_INTEGER_REQUIRED")
    seen = s["seen_intent_ids"]
    if not isinstance(seen, list) or len(seen) > 100 or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in seen):
        return outcome("INVALID", "INVALID_INTENT_EVIDENCE")
    if s["status_build"] != BUILD:
        return outcome("QUARANTINE", "STATUS_IDENTITY_CONFLICT")
    if s["scope"] != s["observed_scope"] or s["route"] != s["observed_route"]:
        return outcome("QUARANTINE", "SCOPE_OR_ROUTE_CONFLICT")
    if s["prior_intent_ambiguous"]:
        return outcome("QUARANTINE", "RECONCILIATION_REQUIRED")
    if max(s["age_seconds"], s["status_age_seconds"], s["fee_age_seconds"]) > 30:
        return outcome("HOLD", "STALE_EVIDENCE")
    if not s["evidence_complete"] or not s["fees_complete"]:
        return outcome("HOLD", "INCOMPLETE_EVIDENCE")
    if not s["market_open"] or not s["exchange_ready"]:
        return outcome("HOLD", "UNAVAILABLE")
    acquired = s["verified_acquired_contracts"]
    exited = s["confirmed_exit_contracts"]
    held = s["position_contracts"]
    reserved = s["reserved_exit_contracts"]
    if held + exited != acquired or reserved > held:
        return outcome("QUARANTINE", "POSITION_EVIDENCE_CONFLICT")
    target = acquired * 3 // 5  # Whole-contract educational model; never round above 60%.
    remaining = max(0, target - exited - reserved)
    quantity, price = min(remaining, held - reserved), 2
    if quantity == 0:
        return outcome("HOLD", "TARGET_ALREADY_COVERED", target_contracts=target)
    fees = s["entry_fee_cents"] + s["exit_fee_cents"]
    net = quantity - fees  # Synthetic 1c entry and 2c exit, total allocated modeled fees.
    if net < 1 or net * 10 < quantity or net < 2 * fees:
        return outcome("DEFER", "FEE_FLOOR_NOT_MET", target_contracts=target,
                       modeled_net_cents=net, modeled_total_fee_cents=fees)
    identity_extra = {"verified_acquired_contracts": acquired, "confirmed_exit_contracts": exited,
                      "reserved_exit_contracts": reserved}
    details = {"target_fraction": "0.60", "target_contracts": target,
               "remaining_target_contracts": remaining, "modeled_net_cents": net,
               "modeled_total_fee_cents": fees}
    identity = {key: s[key] for key in ("market", "round", "side", "scope", "route")}
    identity.update({"action": "sell", "quantity": quantity, "price_cents": price, **identity_extra})
    intent_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if intent_id in seen:
        return outcome("HOLD", "DUPLICATE_INTENT")
    return outcome("PLAN", "SYNTHETIC_PLAN_ONLY", intent_id=intent_id,
                   quantity=quantity, price_cents=price, **details)
