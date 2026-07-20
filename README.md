# Kalshi 15m Sell Bot — Experimental Advanced Dry-Run Learning Preview

> **PUBLIC DRY-RUN PREVIEW — ORDER SUBMISSION DISABLED.** `PUBLIC_PREVIEW_ONLY` is fixed on. Every mutating HTTP request is rejected before signing or transmission. No environment variable, acknowledgment phrase, `--live` option, or direct engine invocation enables orders in this copy.

> **Start with security, not credentials:** read [SECURITY_FIRST.md](SECURITY_FIRST.md), then run `python scripts/verify_release.py` before installing anything.

An advanced dry-run learning build for inspecting sell-side planning on existing Kalshi 15-minute event-contract positions. The retained engine can read positions, orders, fills, market state, fees, and queue conditions, while the public preview keeps every account-changing action unavailable. It is a technical case study in source review, testing, threat modeling, data reconciliation, and bounded automation—not a production trading product.

**This project is not affiliated with, endorsed by, or sponsored by Kalshi. It is not financial advice and has no verified performance record.** Event-contract trading can lose money. This preview defaults to Kalshi’s demo endpoint, dry run, and one cycle; dry run cannot be disabled.

## Verify first

From the extracted project folder:

```bash
python scripts/verify_release.py
python scripts/security_check.py --root .
```

After dependencies are installed:

```bash
python bot.py verify
python bot.py verify --online   # optional: contacts only Kalshi's public demo status endpoint
```

A passing gate means the files match the sealed inventory and the documented safeguards/tests pass. It is **not** a promise that the strategy is profitable, bug-free, or suitable for your account.

## Three-minute start

### Windows

```text
1. Extract the ZIP to a normal folder.
2. Run SETUP_WINDOWS.bat.
3. Run START_WINDOWS.bat.
4. Choose Verify, then Configure, then Dry Run.
```

### macOS or Linux

```bash
./setup.sh
.venv/bin/python bot.py configure
.venv/bin/python bot.py run
```

Use a **Kalshi demo account and demo API key first**. Kalshi documents that demo uses mock funds and separate credentials from production. See [QUICKSTART.md](QUICKSTART.md) for the complete concise flow.

## Operating modes

| Command | Default behavior | Can submit an order? |
|---|---|---:|
| `python bot.py verify` | Hashes, static safeguards, tests | No |
| `python bot.py configure` | Copies a key to private app storage outside the repo | No |
| `python bot.py run` | Dry run ON, configured environment, one cycle | **No — engine blocks every write** |
| `python bot.py run --live` | Fails with preview-only guidance | **No** |
| `python bot.py live` | Fails with preview-only guidance | **No** |
| add `--continuous` | Keeps dry-run observation running | **No** |

The legacy `live` command and `run --live` option remain only to return a clear block message. For an order-capable workflow, use the separately reviewed **10x1c flagship**; do not modify this preview to trade.

## What was sanitized

The preview excludes private workspace material, maintenance utilities, transient output, live-first launchers, project-local key discovery, and internal transfer records. The retained engine is wrapped with a small, testable safety boundary and a preview launcher.

Major changes include:

- Demo endpoint by default and a non-environment-backed `DRY_RUN=True` control.
- Immutable `PUBLIC_PREVIEW_ONLY=True` sentinel enforced by the launcher, engine startup, and final pre-signing mutation boundary.
- Exact allowlists for Kalshi REST and WebSocket origins.
- Redirects, environment proxies, and TLS bypass disabled by default.
- Live/order-capable CLI paths fail with guidance to the separately reviewed 10x1c flagship; the former hidden acknowledgment bypass is removed.
- Fixed sell-only runtime: buy-planning/handoff modules are disabled, and non-sell order creates are rejected before signing.
- Credentials, state, logs, and exports stored outside the repository.
- Private keys must be regular RSA PEM files outside the project folder.
- Bounded ZIP extraction rejects traversal, links, encryption, oversize members, and high compression ratios.
- Crash reports are summary-only unless the operator explicitly opts into sensitive diagnostics.
- Dependencies are exact-version and SHA-256 hash locked.
- Local tests plus GitHub workflows for Ruff, Bandit, pip-audit, secret scanning support, CodeQL, and dependency review.

Read [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for evidence and limits.

## Financial examples are not preview performance

This dry-run preview has no verified live-money performance record and cannot place orders. Any price or quantity shown by the simulator is planning output—not proceeds, profit, or an expected return. See [docs/PROFIT_POTENTIAL.md](docs/PROFIT_POTENTIAL.md) for the distinction between arithmetic examples and evidence.

## Why release it

This began as a practical experiment in turning an idea into a working automation system through rapid iteration. The lasting value came from the finishing work: source review, tests, bounded permissions, reversible defaults, and clear documentation.

This public preview lets reviewers inspect a substantial system and explore
market-automation design without enabling live-money actions. Read
[docs/RELEASE_STORY.md](docs/RELEASE_STORY.md).

## Repository map

- `bot.py` — preview launcher and hard dry-run workflow.
- `public_safety.py` — small independently testable trust boundary.
- `kalshi_15m_sell_bot.py` — retained experimental strategy engine with preview safety boundaries.
- `SECURITY_FIRST.md` — how a user verifies the release before trusting it.
- `SECURITY_AUDIT.md` — findings, changes, checks, and residual risks.
- `LINKEDIN_POST.md` — draft preview copy; not approved for posting.
- `docs/THREAT_MODEL.md` — assets, attackers, controls, and non-goals.
- `tests/` — safety and regression tests.
- `scripts/` — release verification, security gate, and deterministic builder.
- `.github/` — CI security automation and contribution templates.

## Official references

- Kalshi API documentation: <https://docs.kalshi.com/welcome>
- Kalshi demo environment: <https://docs.kalshi.com/getting_started/demo_env>
- Kalshi API keys: <https://docs.kalshi.com/getting_started/api_keys>
- Kalshi rate limits: <https://docs.kalshi.com/getting_started/rate_limits>

## License

Copyright © 2026 Gateway Information Group LLC.

This public dry-run preview is released under the [MIT License](LICENSE.md).
The deliberate owner decision is documented in
[LICENSE_OPTIONS.md](LICENSE_OPTIONS.md), and dependency obligations remain in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
