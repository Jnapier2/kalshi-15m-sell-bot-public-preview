# Kalshi 15-Minute Sell Preview

**Fresh public preview based on the v41.65 evidence-coherence lineage.**

This offline tool turns a sanitized position, fee, route, and status snapshot
into a deterministic sell-side planning result. It models the fixed public
preview contract: one durable **40% target at exactly 2¢**, subject to complete
and coherent fee and exchange-route evidence.

> **Live writes are absent by construction.** This repository has no network
> client, credential loader, request signer, or account mutation code. It cannot
> connect to Kalshi, submit an order, cancel an order, or move funds.

## Quick start

```bash
python scripts/verify_release.py
python -I -S run_sell_preview.py examples/eligible_exit_snapshot.json
python -m unittest discover -s tests -v
```

The public entrypoint requires Python isolated/no-site mode so a local shadow
module cannot run before release verification. On Windows,
`Kalshi15mSellPreview.bat examples\eligible_exit_snapshot.json` is the single
BAT convenience launcher and applies those flags automatically.

## Fixed public preview contract

| Property | Value |
| --- | ---: |
| Target fraction | `40%` of eligible contracts |
| Economic exit price | `2¢` |
| Minimum projected net | `1.00¢` total |
| Minimum projected net per contract | `0.10¢` |
| Minimum net-to-total-fees ratio | `2.00×` |
| Network access | None |
| Credential support | None |
| Live write authority | None |

The planner emits `PLAN`, `DEFER`, `HOLD`, `QUARANTINE`, or `INVALID`.
Fee evidence that does not clear the fixed thresholds produces `DEFER`, not a
different price or target. Conflicting shard evidence or stale/mismatched
current-status evidence produces `QUARANTINE`.

## Evidence reviewed

- Open market and positive eligible position.
- Bounded market-data and current-status age.
- Current-status build identity.
- Complete sell and fee evidence.
- Intended shard versus observed route evidence.
- Existing exit-order coverage to prevent duplicate planning.
- Fixed fee-policy thresholds.
- Deterministic plan identity.

## What changed from the previous public preview

- Updated the lineage from v41.22.3 to v41.65.
- Removed credential configuration, public/demo network reads, and all retained
  mutation-capable engine code from active `main`.
- Added route-efficiency evidence, shard-conflict quarantine, current-status
  build/age coherence, and fee-policy truth.
- Added a lean standard-library-only source tree, normalized manifest verifier,
  synthetic examples, and one thin Windows launcher.
- Preserved the repository URL and history while replacing the active source.

Read [PUBLIC_STERILIZATION_REPORT.md](PUBLIC_STERILIZATION_REPORT.md),
[SECURITY.md](SECURITY.md), and [DISCLAIMER.md](DISCLAIMER.md).

## License

MIT. Copyright © 2026 Gateway Information Group LLC. All rights reserved.

This project is independent and is not affiliated with, endorsed by, or sponsored
by Kalshi.
