# Changelog

## 41.22.2-public-preview — 2026-07-19

### Hard-blocked dry-run preview

- Added the literal, non-environment-backed `PUBLIC_PREVIEW_ONLY=True` sentinel.
- Fixed engine `DRY_RUN=True` and `FORCE_LIVE_RUN=False` instead of reading those controls from the environment.
- Blocked every non-GET request at the final pre-signing boundary.
- Removed the hidden acknowledgment argument and all acknowledgment-based unlocking.
- Changed `python bot.py run --live` and `python bot.py live` to fail with guidance to the separately reviewed 10x1c flagship.
- Added regression tests for hostile environment values, runtime flag mutation, direct engine calls, removed `--ack` parsing, and pre-signing rejection.
- Relabeled the package as an experimental advanced dry-run learning preview that is neither licensed nor approved for publication.

### Retained sell-planning scope

- Removed or qualified launch, production-readiness, and performance language in preview-facing copy.
- Clarified that this copy simulates sell planning for positions already held and cannot place orders.
- Disabled inherited buy-planning, buy-handoff, cross-bot, and entry-planning modules in the public runtime.
- Added a central pre-signing validator for legacy and V2 order-create payloads, including contract-side/client-ID mapping for V2.
- Added regression checks proving non-sell creates fail before signing and buy-planning modules remain disabled.

## 41.22.1-public — 2026-07-18

### Security posture

- Changed the default API environment from production to demo.
- Changed the default from live execution to dry run.
- Added an exact live-order acknowledgment enforced in launcher and engine.
- Added exact Kalshi REST and WebSocket origin allowlists.
- Disabled HTTP redirects, environment proxy inheritance, and caller-controlled TLS bypass by default.
- Moved credentials, config, state, logs, and exports outside the repository.
- Removed project-local key discovery; require a regular external RSA PEM key of at least 2048 bits.
- Added bounded regular-file-only ZIP extraction.
- Changed crash diagnostics to summary-only by default.
- Added exact-version, SHA-256 hash-locked dependencies and a lock-derived CycloneDX 1.6 SBOM.
- Forced an explicit certifi CA bundle and resolved the Windows process probe through `%SystemRoot%\System32`.

### Public usability

- Replaced live-first batch entry points with `bot.py`, `SETUP_WINDOWS.bat`, `START_WINDOWS.bat`, and `setup.sh`.
- Added security-first verification, quick start, risk, privacy, FAQ, portfolio copy, threat model, architecture, and vibecoding learning materials.
- Added local safety/regression tests and GitHub security workflows.

### Sanitization

- Excluded private workspace material, maintenance utilities, transient output, transfer records, legacy shims, and the internal setup writer.
- Confirmed the supplied archives contained no actual API key or private key material under the documented scan patterns.
- Fixed inherited undefined-name defects detected during stricter static analysis.
- Added deterministic manifest/archive metadata and SBOM-to-lock consistency tests.

### Important

- Strategy behavior remains complex and has not been represented as independently profitable or formally verified.
- The owner must select a public-use license before publication.
