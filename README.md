# Kalshi 15-Minute Sell Preview

An offline educational exit planner demonstrating a 60% target at 2¢, fee and freshness checks, and duplicate-intent protection. It has no account access or live orders.

## Quick start

Python 3.11 or newer; no runtime packages or account setup are required.

```console
python -I -S -B run_sell_preview.py --demo
python -I -S -B run_sell_preview.py --verify
python -I -S -B run_sell_preview.py --menu
python -I -S -B run_sell_preview.py examples/conflict_snapshot.json
python -I -S -B run_sell_preview.py --export
python -B -m unittest discover -s tests -v
```

On Windows, run `Kalshi15mSellPreview.bat` for the synthetic demo or pass `--menu` for grouped Start, Reports, and Setup actions. `Kalshi15mSellPreview_Export.bat` independently creates a minimal support ZIP under `outputs/support/`. Both launchers locate the project from their own directory; neither installs software or changes security settings.

## What the planner demonstrates

60% of cumulative verified 1¢ acquisitions at exactly 2¢, rounded down to whole contracts. Confirmed exits and reserved exits reduce the remaining target. The candidate is capped by unreserved same-scope holdings. New acquisitions may raise the target; exit fills alone do not. This deliberately simplified public model does not migrate legacy targets or model fractional contracts.

Each snapshot must be explicitly synthetic, use `SYNTHETIC-` identifiers, and provide complete, typed inputs. The planner checks scope and route agreement, status identity, market readiness, bounded evidence age, fee completeness, and prior-intent evidence. Unknown fields, malformed values, duplicate JSON keys, oversized inputs, and non-finite numbers are rejected without echoing their contents.

Modeled net = candidate quantity × (2¢ − 1¢) − allocated entry fees − modeled exit fees. All fee inputs are totals in whole cents for this candidate, not per-contract fees or a current Kalshi fee schedule. Net must be at least 1¢ total, 0.10¢ per contract, and 2× total modeled fees. Otherwise the result is DEFER; price and target do not change.

Results are `PLAN`, `HOLD`, `QUARANTINE`, `INVALID`, or `DEFER`. `PLAN` is educational output only. Freshness means supplied ages are no more than 30 seconds; this offline tool cannot authenticate those ages or confirm real exchange state.

Duplicate prevention is deterministic comparison against supplied intent IDs and exposure evidence. Ambiguous prior intent requires reconciliation. It is not a durable execution ledger, a multi-process lock, or a guarantee about live orders.

## Public boundary

There is no transport, signing, credential loading, account access, order submission, cancellation, fund movement, or hidden live-mode option. Samples are invented. Do not use private account exports as inputs.

Package verification checks exact managed hashes and release identity before planner imports. Python isolated/no-site/no-bytecode flags prevent project-local import shadowing on the canonical entrypoint. Checksums detect changes against the supplied manifest; they are not a publisher signature. Only `.git/` and the non-executable `outputs/` area are excluded from the payload inventory.

The independent Export20 path emits four generated files without reading input snapshots, logs, source, credentials, environment variables, or account records. An integrity failure attempts one bounded local export and exits; a failed export is reported, not retried recursively.

## Release and evidence

Public version `41.84-public.1` is an educational reimplementation informed by source lineage `41.84.0`, not a redacted live bot or a release of that private engine. The active repository tree is replaced in full while its URL, history, MIT license, public title, execution namespace, and canonical launcher are preserved.

See [VALIDATION.md](VALIDATION.md), [PUBLIC_STERILIZATION_REPORT.md](PUBLIC_STERILIZATION_REPORT.md), and [SECURITY.md](SECURITY.md). Local tests are not evidence of native Windows, antivirus clearance, live exchange correctness, or profitability. GitHub Actions results, when available, are separate evidence tied to their commit.

## License

MIT; see [LICENSE](LICENSE). Copyright © 2026 Gateway Information Group LLC. All rights reserved.

Independent project; not affiliated with, endorsed by, or sponsored by Kalshi.
