# Kalshi 15-Minute Sell Preview

An offline educational exit planner demonstrating cost-backed price selection, fee and freshness checks, and duplicate-intent protection. It has no account access or live orders.

## Try the demonstration

Python 3.11 or newer is required. There are no third-party runtime packages, accounts, keys, installations, or network calls.

```console
python -I -S -B run_sell_preview.py --demo
python -I -S -B run_sell_preview.py --menu
python -I -S -B run_sell_preview.py --verify
python -I -S -B run_sell_preview.py examples/conflict_snapshot.json
python -I -S -B public_support.py --export
python -B -m unittest discover -s tests -v
```

Windows: `Kalshi15mSellPreview.bat` runs the demo; add `--menu` for grouped Explore and Support actions. `Kalshi15mSellPreview_Export.bat` calls the standalone support module, not the main application. Both use their own directory rather than the caller's working directory. They never install software, elevate privileges, or change security settings.

## What it demonstrates

The public model calculates a **60% whole-contract target** from cumulative supplied acquisitions, then subtracts confirmed exits and reserved exits. It never increases the target because an exit filled. This is stateless teaching arithmetic, not the private engine's durable acquisition-tranche ledger.

The default demo reviews cost-backed LIMIT prices no higher than 2¢. Every candidate tick must independently cover the full supplied acquisition-packet cost, its entry fees, and the worse of that tick's supplied maker/taker fee estimates. The unsold remainder is valued at zero. Required modeled net remains at least 1¢ total, 0.10¢ per proposed contract, and twice total modeled entry/exit fees.

When fresh supplied bid depth covers the candidate, the highest qualifying reachable tick is selected. Otherwise explicit synthetic passive permission allows a cost-backed offer: a qualifying tick below the supplied competing ask, a preserved qualifying own quote when no competitor exists, or the lowest qualifying tick near close. Missing liquidity is not a buyer or fill. Incomplete cost proof holds; no qualifying tick defers. After prior confirmed exits, this simplified adaptive path defers rather than modeling a reprice.

The fixture produces six proposed contracts at 1.50¢, with **$0.06 modeled packet net**, using entirely invented costs and fees. No fill is expected or claimed. The original fixed-2¢ teaching example remains available as `examples/eligible_exit_snapshot.json`.

**Public-model distinction:** selected cost-backed planning ideas are reimplemented from v41.90.0. Private credential handling, live clients, cost-proof recovery, automatic amendments, acquisition ledgers and trading authority are absent. The preview is not a feature-equivalent copy of that engine.

## Inputs and results

The legacy fixed-price schema uses `entry_fee_cents` and `exit_fee_cents`, totals in whole cents for its candidate and an explicit 1¢ entry assumption. The alternative cost-backed schema replaces both fields with `cost_model`; mixing the two is rejected.

Within `cost_model`, **one integer unit is $0.0001 (0.01¢)**. `packet_cost_units` and `packet_entry_fee_units` cover the entire acquisition packet. Each tick supplies total candidate maker/taker fees separately; no current exchange fee schedule is embedded. `bids` are supplied depth levels; `competing_ask_units` must already exclude the owner's displayed quantity. Book age above two seconds cannot establish fresh executable depth. Main market/status/fee ages above 30 seconds block planning.

Example arithmetic: 6 × 150 units − 100 cost units − 100 entry-fee units − 100 exit-fee units = 600 units ($0.06). This is a synthetic calculation, not profit evidence.

Inputs must be explicitly synthetic and use `SYNTHETIC-` identifiers. Unknown fields, conflicting scopes, duplicate JSON keys, non-finite values, malformed numbers, oversized inputs and non-regular input files are rejected. Do not provide private account exports. Snapshot values are assertions supplied by the caller; this tool cannot establish real exchange truth.

Results are `PLAN`, `HOLD`, `QUARANTINE`, `INVALID` or `DEFER`. `PLAN` is educational output without execution authority. Duplicate protection compares deterministic IDs with supplied prior IDs and exposure evidence; it is not a durable order ledger or multi-process trading guarantee.

## Privacy and integrity

There is no credential loader, transport, request signer, account access, order submission, cancellation, fund movement or hidden live switch. Only reviewed public source, synthetic fixtures, tests and documentation are included; private source archives are not redistributed.

The canonical entrypoint requires isolated/no-site/no-bytecode Python. It verifies exact managed payload hashes and package identity before planner imports, and checks the independent support helper against a built-in digest. Downloaded bootstrap code and the Python runtime still require a trusted source. A manifest is not a publisher signature and does not defeat an attacker replacing all code and trust records.

Support exports contain **four generated safe records**, never inputs, logs, source, credentials or environment values. Files stay under `outputs/support/`. Critical integrity failures attempt an atomic capsule followed by a ZIP using already trusted support code. Unknown input or ordinary cancellation does not trigger Critical capture. `CAPSULE_ONLY`, unavailable and successful minimal capture remain distinct.

Exports use a same-machine lock, 32 KiB per-file/ZIP bound, one MiB free-space minimum and a 64-attempt persistent budget. They do not prune evidence or scan user folders. A preserved stale lock or exhausted budget blocks further capture; retain the existing evidence and use a clean verified public package. Byte/operation limits are not a hard deadline against stalled OS storage. Missing Python or an untrusted bootstrap can make capture unavailable. No fallback changes protections or executes a damaged helper.

## Release and evidence

Version `41.90-public.1`. Existing public title, repository URL, execution namespace, canonical main/Export BAT names, MIT license and third-party notices are retained. The active tree is replaced; historical commits, branches, tags, releases and cached copies are not erased or certified.

See [VALIDATION.md](VALIDATION.md), [PUBLIC_STERILIZATION_REPORT.md](PUBLIC_STERILIZATION_REPORT.md), [SECURITY.md](SECURITY.md), and [SBOM.cdx.json](SBOM.cdx.json). Local tests, GitHub-hosted CI, Norton status and live financial behavior are separate evidence. No profitability, antivirus clearance, or testing on the owner's computers is claimed.

## License

MIT; see [LICENSE](LICENSE). Copyright © 2026 Gateway Information Group LLC. All rights reserved.

Independent project; not affiliated with, endorsed by, or sponsored by Kalshi.
