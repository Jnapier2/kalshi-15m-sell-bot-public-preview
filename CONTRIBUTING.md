# Contributing

Contributions should preserve the security posture and make behavior easier to inspect.

## Before opening a pull request

1. Use demo and dry-run evidence; never include real credentials or account data.
2. Run `python scripts/security_check.py --strict`.
3. Run Ruff, Bandit, and pip-audit using `requirements-dev.lock.txt`.
4. Add or update tests for every safety, parsing, network, archive, authentication, or order-path change.
5. Update documentation and `CHANGELOG.md` when user-visible behavior changes.

## Non-negotiable defaults

Pull requests must not make production, continuous execution, proxy inheritance, sensitive crash exports, project-local keys, TLS bypass, redirects, or order submission easier to trigger by accident.

## Scope discipline

The retained engine is large. Prefer small reviewable changes, explicit invariants, and tests over broad generated rewrites. Separate mechanical formatting from behavioral changes.

## Financial claims

Do not submit guaranteed-return language, fabricated results, cherry-picked performance, or unrepeatable profit claims. Clearly label simulations, demo results, backtests, and assumptions.

## License status

External contributions should not be accepted until the owner selects a repository license and a contribution policy.
