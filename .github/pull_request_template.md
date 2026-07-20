## Change

Describe the smallest reviewable behavior change.

## Evidence

- [ ] `python scripts/security_check.py --strict`
- [ ] Ruff undefined-name/syntax checks
- [ ] Bandit medium/high scan
- [ ] pip-audit after dependency changes
- [ ] Demo/dry-run evidence where applicable
- [ ] Checksums/manifest regenerated

## Safety impact

Explain effects on endpoints, redirects/proxies/TLS, credentials, storage, archives, logs, live authorization, quantities, fees, and rollback behavior.

## Claims

- [ ] No credentials or private account data are included.
- [ ] No profit is guaranteed or implied.
- [ ] Demo, simulation, backtest, and production evidence are clearly separated.
