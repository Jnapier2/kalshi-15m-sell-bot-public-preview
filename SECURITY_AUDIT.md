# Security Audit and Release-Hardening Report — Dry-Run Preview

**Build:** `41.22.2-public-preview`  
**Audit date:** July 19, 2026  
**Owner metadata:** Gateway Information Group LLC  
**Audit type:** Best-effort source review, hardening, packaging, and local verification—not a third-party penetration test or financial-performance certification.

## Security verdict first

| Question | Verdict |
|---|---|
| Is this package suitable for controlled **demo/dry-run review**? | **Yes, as an experimental preview with documented residual risk.** Every mutating request is hard-blocked in the unmodified copy. |
| What remains before broader use? | Keep the preview dry-run only, maintain the verification gates, and complete independent review before any order-capable edition. |
| What is the production posture? | Production capability is intentionally unavailable in this preview. The retained engine remains an experimental learning system rather than a formally certified trading product. |
| What does it show about performance? | Planning behavior and conditional arithmetic only. It makes no profit or loss-prevention promise. |

A passing verification means the files match the current preview inventory and the documented baseline safeguards are present. It does not prove every strategy branch correct, protect a compromised computer, establish production suitability, or demonstrate profitability.

## Scope and provenance

The public preview is limited to the engine, its small safety boundary and launcher, tests, user documentation, dependency records, and packaging tools. The sealed inventory makes that boundary reviewable.

The review covered source and batch files, dependency declarations, credential handling, authenticated network destinations, TLS/proxy behavior, order authorization, runtime storage, archive extraction, diagnostic privacy, release integrity, and public-facing claims.

## Highest-impact findings in the supplied bot

| Severity | Finding | Preview disposition |
|---|---|---|
| Critical | `DRY_RUN=0` and the production API were defaults; the primary launcher promoted live mode and forcibly disabled dry run. | **Fail-closed preview.** `PUBLIC_PREVIEW_ONLY=True`, `DRY_RUN=True`, and `FORCE_LIVE_RUN=False` are fixed in source. Legacy live CLI paths fail with 10x1c flagship guidance, and every non-GET request is rejected at the final pre-signing boundary. |
| High | Inherited buy-candidate, buy-handoff, and entry-planning modules were enabled despite the public project being presented as a sell bot. | **Fixed.** The public runtime now hard-disables those modules, and every order-create request must pass a pre-signing sell-only validator. Legacy payloads require `action=sell`; V2 payloads must match the managed client-ID contract side and its corresponding YES-book side. |
| Critical | `KALSHI_BASE_URL` could be custom while signed headers were sent to it. A bad local setting could disclose the API Key ID, timestamp, and signature to an attacker-controlled host. | **Fixed.** Authenticated REST and WebSocket traffic is restricted to exact official demo/production origins and validated paths. |
| High | Requests inherited environment proxies, `.netrc`, redirects, and caller-controlled TLS settings. | **Fixed.** `trust_env=False`, empty proxies, no redirects, a pinned certifi CA bundle, and TLS 1.2+ are enforced. Custom CA/proxy/client-certificate overrides are rejected. |
| High | The setup model favored a project-local unencrypted private key and a local batch config that set live mode. | **Fixed.** Configuration and keys are external to the repository; repository-local keys are rejected; Unix owner-only permissions are checked. |
| High | Dependency ranges were broad and unhashed. | **Fixed.** Runtime and maintainer lock files use exact versions plus SHA-256 hashes; setup requires binary distributions and `--require-hashes`. |
| High | Operational data, transient output, transfer records, and live-first compatibility launchers were mixed into the working set. | **Addressed for this preview.** They were removed. The preview contains the engine, small safety boundary and launcher, tests, docs, and packaging tooling. |
| Medium | Support ZIP extraction guarded basic traversal but had no member-count, size, compression-ratio, encryption, or link limits. | **Fixed.** Extraction is bounded and regular-file-only, with explicit traversal, link, device, encryption, size, count, and compression-bomb rejection. |
| Medium | Crash reports included tracebacks, paths, state summaries, and log tails by default. | **Fixed.** Reports are summary-only and redacted unless a user deliberately enables sensitive diagnostics. |
| Medium | The inherited engine contained undefined-name defects that syntax compilation did not detect. | **Fixed.** Undefined-name analysis and targeted regression tests were added; the identified defects were repaired. |
| Low | A Windows process probe invoked `tasklist` by a partial executable name. | **Fixed.** It now resolves the executable from `%SystemRoot%\\System32` and fails closed if unavailable. |

No private key, usable API credential, personal email address, absolute user-home path, native executable, driver, packer, obfuscator, persistence mechanism, or antivirus/security-disable routine was found in the supplied archive. A PEM-looking string in the old maintenance toolbox was a redaction pattern and replacement example, not key material.

## Preview safety architecture

The preview adds two small, reviewable layers around the retained engine:

- `public_safety.py` owns the literal preview sentinel, rejects mutating methods, and validates exact network origins/paths, private-key location/shape, external storage, identifier masking, and redaction.
- `bot.py` owns the preview workflow: verify first, configure externally, require dry run, and reject legacy live commands before loading configuration or launching a child.

The engine independently fixes dry run on, ignores force-live environment values, checks the preview sentinel at startup, and rejects every non-GET request at the final pre-signing boundary. This protects the unmodified preview from stale environments, hidden acknowledgments, runtime flag changes, and direct engine invocation. A user who deliberately rewrites the source creates a different, unreviewed program.

## Supply-chain and release controls

- Exact-version, SHA-256 hash-locked runtime and developer dependencies.
- Fresh-lock installation succeeded in a clean virtual environment; `pip check` and imports succeeded.
- Deterministic CycloneDX 1.6 SBOM generated from the runtime lock.
- SBOM component inventory is checked against the lock file using only the Python standard library.
- Every retained release file is whitelisted in `MANIFEST.json` and hashed in `SHA256SUMS.txt`.
- The deterministic builder uses fixed timestamps and stable ordering and can produce a ZIP with a SHA-256 sidecar.
- GitHub workflows are included for Python 3.10–3.13 tests, Ruff, Bandit, `pip-audit`, detect-secrets, CodeQL, dependency review, and Dependabot.

The GitHub Actions references use current major-version tags rather than immutable commit SHAs. Before a high-assurance production release, pin each action to a reviewed full commit SHA and let Dependabot propose deliberate updates.

## Verification evidence

### Pre-seal and final local checks

- Python compilation: **pass**.
- Complete preview unit suite: **62 tests discovered; 60 passed and 2 platform-specific tests skipped on Windows**.
- Ruff: **pass**.
- Bandit medium/high threshold: **0 findings**.
- Full Bandit inventory: **134 low-severity findings**—111 broad exception-pass patterns, 8 exception-continue patterns, 5 false-positive “password” literals, 4 fixed-argument subprocess calls, 3 subprocess imports, and 3 non-cryptographic PRNG uses. These remain review debt; this report does not characterize the full Bandit scan as finding-free.
- detect-secrets: **0 candidates** after excluding generated lock/SBOM/inventory files and explicitly annotated provenance checksums.
- Fresh exact hash-locked developer/runtime installation: **pass**.
- Installed dependency consistency (`pip check`): **pass**.
- CycloneDX 1.6 strict schema validation: **pass**.
- POSIX setup script syntax (`bash -n setup.sh`): **pass**.
- Preview mutation-boundary tests: **pass**—hostile environment values, runtime flag changes, removed acknowledgment arguments, direct engine calls, and pre-signing mutation attempts are covered.

### Dependency vulnerability status

A local `pip-audit` run was attempted but could not reach `pypi.org` because DNS/network access was unavailable in the audit sandbox. Therefore this report does **not** claim a completed vulnerability-database audit. The repository workflow runs `pip-audit` on every push and pull request; the owner should require that online job to pass immediately before publishing each release.

### Final sealed evidence

- Release integrity and whitelist verification: **pass** (`53` checksum records; `54` total release files including `SHA256SUMS.txt`; `52` records in the non-recursive manifest inventory).
- Strict built-in security gate: **pass**.
- Preview unit suite with updated inventory present: **62 tests discovered; 60 passed and 2 platform-specific tests skipped on Windows**.
- Final manifest timestamp: deterministic `2026-07-19T18:00:00Z`.
- The current preview engine SHA-256 is recorded in `MANIFEST.json` after each reviewed source change.
- Earlier deterministic-build evidence—including a 60-member ZIP structure check—applied to a predecessor package. The current preview is MIT-licensed and published as source with a 54-file release inventory; no packaged archive is currently claimed.
- Local inventory verification, the baseline security gate, Ruff, and all applicable tests must pass before any reviewer handoff.

## User verification procedure

Before entering credentials:

```bash
python scripts/verify_release.py
python scripts/security_check.py --root .
```

After installing the exact locked dependencies:

```bash
python bot.py verify
```

If a packaged archive is published in the future, compare its SHA-256 with the separately published sidecar and confirm that it came from the official repository or release channel. See `SECURITY_FIRST.md` for Windows, macOS, and Linux commands.

## Residual risks and unverified areas

1. **Large retained engine:** roughly 38,000 lines, heavy global state, broad exception handling, and concurrent REST/WebSocket behavior remain difficult to exhaustively reason about. Inactive inherited buy-analysis code remains for provenance even though the public runtime disables its planning/handoff modules and blocks non-sell creates.
2. **No live-money validation in this audit:** no production authentication, order submission, fill, amendment, cancellation, rate-limit, maintenance, or settlement test was performed.
3. **No native Windows execution in this audit:** Windows batch flow and Windows ACL behavior require testing on a clean Windows host. On Windows, external key protection relies primarily on the current user profile’s ACLs; this package does not install a custom ACL or encrypt the private key with DPAPI.
4. **No third-party penetration test or formal verification.**
5. **No profitability proof:** demo behavior, arithmetic examples, and passing software tests do not establish a repeatable market edge.
6. **External systems change:** API schemas, rate limits, fees, market rules, eligibility, dependencies, and certificates require ongoing review.
7. **Local compromise remains out of scope:** malware or an administrator can read keys, alter code, or interfere with traffic and process state.
8. **License scope:** the preview is MIT-licensed, but downstream users remain responsible for third-party terms, platform rules, and their own use.

## Broader-use gates

Do not represent this preview as order-capable, production-ready, or broadly supported. Any broader release would require:

1. Current online security workflows, including dependency auditing, CodeQL, dependency review, and secret scanning.
2. Private vulnerability reporting and a repository-specific advisory path.
3. Clean-machine setup, verification, configuration, and dry-run testing on Windows and a Unix-like system.
4. Exact release-archive hash, inventory, and security verification after download.
5. Demo or fabricated data in screenshots and video.
6. Separate specialist review before any order-capable or production operation.

## Bottom line

The original live-first prototype required a narrower public boundary. This
MIT-licensed build is therefore an experimental advanced dry-run learning
preview with every mutating request hard-blocked. It is not a production
trading product or a performance-marketing claim. Any order-capable workflow
belongs in the separately reviewed 10x1c flagship.
