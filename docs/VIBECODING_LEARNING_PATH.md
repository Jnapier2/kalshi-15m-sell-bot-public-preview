# Vibecoding Learning Path

Use this repository as a guided study rather than a one-click trading product.

## 1. Trust boundary

Read `public_safety.py` first. Identify every place where untrusted strings become URLs, paths, credentials, archive members, or preview-control inputs. Confirm that no input can enable mutation, then add one adversarial safety test.

## 2. Launcher and intent

Read `bot.py`. Trace how demo/dry-run/one-cycle defaults are constructed and how stale environment variables are removed. Explain why the engine independently repeats the live-authorization check.

## 3. Authentication

Find `create_signature` and `signed_request_at_base` in the engine. Study timestamp + method + path signing and why the query string is not included in the signed path. Use only demo credentials.

## 4. State and reconciliation

Trace positions, open orders, fills, client order IDs, retries, and ambiguous responses. Write down the invariants required to avoid duplicate or contradictory actions.

## 5. Economics

Follow fee-profile selection, rounding, minimum edge, quantity thresholds, and configurable sell-coverage logic. Reproduce the sell-only profit arithmetic from a user-supplied cost basis and list every assumption.

## 6. Concurrency and WebSockets

Study public/private event queues, reconnects, REST fallback, stale-data guards, and how out-of-order events could affect state. Add a deterministic test for one ordering problem.

## 7. Supply chain

Inspect the hash locks, manifest, release verifier, SBOM, and GitHub workflows. Deliberately change one byte and observe the verifier fail.

## 8. Responsible release

Review the threat model, privacy policy, license gate, and publishing checklist. Practice writing a claim that distinguishes intended behavior, verified evidence, and unverified risk.

## A good vibecoding loop

1. State the invariant before asking for code.
2. Ask for the smallest reviewable change.
3. Inspect the diff, not only the explanation.
4. Add an adversarial test.
5. Run static and runtime checks.
6. Preserve a known-good rollback point.
7. Document what remains uncertain.

AI can accelerate implementation. Evidence earns trust.
