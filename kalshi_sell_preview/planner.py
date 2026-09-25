"""Deterministic synthetic-data planner. No transport or credential surface."""
import hashlib
import json
import re

BUILD = "KALSELL-PUBLIC-41.90.1-COST-REVIEW"
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
    if not isinstance(snapshot, dict) or set(snapshot) not in (REQUIRED, (REQUIRED - {"entry_fee_cents", "exit_fee_cents"}) | {"cost_model"}):
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
        if key not in s:
            continue  # The alternate cost schema omits the legacy whole-cent fee fields.
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
    identity_extra = {"verified_acquired_contracts": acquired, "confirmed_exit_contracts": exited,
                      "reserved_exit_contracts": reserved}
    details = {"target_fraction": "0.60", "target_contracts": target,
               "remaining_target_contracts": remaining}
    if "cost_model" in s:
        decision = cost_backed_price(s["cost_model"], quantity, exited)
        if decision["status"] != "PLAN":
            return outcome(decision["status"], decision["reason"], target_contracts=target)
        price_units = decision.pop("price_units")
        price = price_units // 100 if price_units % 100 == 0 else f"{price_units / 100:.2f}"
        decision.pop("status")
        decision.pop("reason")
        details.update(decision, price_units=price_units)
    else:
        fees = s["entry_fee_cents"] + s["exit_fee_cents"]
        net = quantity - fees  # Explicit legacy educational 1c entry assumption.
        if net < 1 or net * 10 < quantity or net < 2 * fees:
            return outcome("DEFER", "FEE_FLOOR_NOT_MET", target_contracts=target,
                           modeled_net_cents=net, modeled_total_fee_cents=fees)
        details.update(modeled_net_cents=net, modeled_total_fee_cents=fees)
    identity = {key: s[key] for key in ("market", "round", "side", "scope", "route")}
    identity.update({"action": "sell", "quantity": quantity, "price_cents": price, **identity_extra})
    intent_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if intent_id in seen:
        return outcome("HOLD", "DUPLICATE_INTENT")
    return outcome("PLAN", "SYNTHETIC_PLAN_ONLY", intent_id=intent_id,
                   quantity=quantity, price_cents=price, **details)


def cost_backed_price(model, quantity, exited):
    """Synthetic integer-unit price review, not a transport or exchange fee quote.

    One unit is $0.0001 (0.01 cent). Every supplied tick is checked independently.
    The candidate must cover the whole acquisition packet; remainder value is zero.
    """
    fields = {"proof_complete", "packet_cost_units", "packet_entry_fee_units", "ticks",
              "bids", "book_age_seconds", "passive_allowed", "competing_ask_units",
              "own_quote_units", "seconds_to_close"}
    if not isinstance(model, dict) or set(model) != fields:
        return {"status": "INVALID", "reason": "COST_SCHEMA_MISMATCH"}
    m = model
    integer = lambda value, maximum=100000000: type(value) is int and 0 <= value <= maximum
    if any(type(m[key]) is not bool for key in ("proof_complete", "passive_allowed")):
        return {"status": "INVALID", "reason": "COST_BOOLEAN_REQUIRED"}
    if any(not integer(m[key]) for key in ("packet_cost_units", "packet_entry_fee_units", "book_age_seconds", "seconds_to_close")):
        return {"status": "INVALID", "reason": "COST_INTEGER_REQUIRED"}
    if any(m[key] is not None and (not integer(m[key], 10000) or m[key] == 0) for key in ("competing_ask_units", "own_quote_units")):
        return {"status": "INVALID", "reason": "INVALID_QUOTE"}
    ticks, bids = m["ticks"], m["bids"]
    if not isinstance(ticks, list) or not 1 <= len(ticks) <= 200 or not isinstance(bids, list) or len(bids) > 100:
        return {"status": "INVALID", "reason": "BOUNDED_BOOK_REQUIRED"}
    prices = set()
    for row in ticks:
        if not isinstance(row, dict) or set(row) != {"price_units", "maker_fee_units", "taker_fee_units"}:
            return {"status": "INVALID", "reason": "INVALID_TICK"}
        p = row["price_units"]
        if not integer(p, 200) or p == 0 or p in prices or any(not integer(row[k]) for k in ("maker_fee_units", "taker_fee_units")):
            return {"status": "INVALID", "reason": "INVALID_TICK"}
        prices.add(p)
    bid_prices = set()
    for row in bids:
        if not isinstance(row, dict) or set(row) != {"price_units", "quantity"}:
            return {"status": "INVALID", "reason": "INVALID_BID"}
        if not integer(row["price_units"], 10000) or not integer(row["quantity"], 1000000) or row["price_units"] in bid_prices:
            return {"status": "INVALID", "reason": "INVALID_BID"}
        bid_prices.add(row["price_units"])
    if not m["proof_complete"]:
        return {"status": "HOLD", "reason": "COST_PROOF_INCOMPLETE"}
    if exited:
        return {"status": "DEFER", "reason": "ADAPTIVE_AFTER_FILL_DEFERRED"}
    if m["seconds_to_close"] == 0:
        return {"status": "HOLD", "reason": "MARKET_CLOSED"}
    qualified = {}
    for row in ticks:
        price = row["price_units"]
        fee = max(row["maker_fee_units"], row["taker_fee_units"])
        net = quantity * price - m["packet_cost_units"] - m["packet_entry_fee_units"] - fee
        if net >= 100 and net >= 10 * quantity and net >= 2 * (m["packet_entry_fee_units"] + fee):
            qualified[price] = (net, fee)
    if not qualified:
        return {"status": "DEFER", "reason": "NO_COST_SAFE_TICK"}
    fresh = m["book_age_seconds"] <= 2
    reachable = [p for p in qualified if fresh and sum(row["quantity"] for row in bids if row["price_units"] >= p) >= quantity]
    if reachable:
        selected, basis = max(reachable), "SUPPLIED_FRESH_BID_DEPTH"
    elif not m["passive_allowed"]:
        return {"status": "HOLD", "reason": "NO_FRESH_DEPTH_AND_PASSIVE_DISABLED"}
    else:
        ask = m["competing_ask_units"] if fresh else None
        own = m["own_quote_units"]
        close = m["seconds_to_close"] <= 120
        if ask is None and own in qualified and not close:
            selected, basis = own, "PRESERVED_OWN_COST_SAFE_QUOTE"
        elif ask is not None and not close:
            selected = max((p for p in qualified if p < ask), default=min(qualified))
            basis = "COMPETITIVE_COST_BACKED_LIMIT"
        else:
            selected, basis = min(qualified), "COST_FLOOR_LIMIT_LIQUIDITY_UNKNOWN"
    net, fee = qualified[selected]
    return {"status": "PLAN", "reason": "SYNTHETIC_COST_REVIEW_ONLY", "price_units": selected,
            "pricing_basis": basis, "modeled_net_units": net, "modeled_exit_fee_units": fee,
            "unit_dollars": "0.0001", "remaining_position_value_units": 0, "expected_fill": False}
