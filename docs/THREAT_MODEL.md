# Threat Model

## Assets

- Kalshi private key and API Key ID
- Account balance, positions, orders, and fills
- Ability to submit, amend, or cancel orders
- Local runtime state and logs
- Release integrity and dependency provenance
- User trust and financial decision-making

## Primary threats and controls

| Threat | Control |
|---|---|
| Credential sent to attacker-controlled host | Exact REST/WebSocket allowlists; API-path validation; redirects refused |
| Credential exposed through proxy/netrc/environment | `trust_env=False` by default; launcher removes proxy/netrc variables |
| Accidental or attempted live execution | Literal preview sentinel; fixed dry-run flag; live CLI block; final pre-signing rejection of every mutating method |
| Private key committed or packaged | Project-folder keys rejected; `.gitignore`; secure external config store |
| State/logs leak through repository | Runtime/export directories required outside repository |
| Malicious or accidental ZIP traversal/bomb | Count, size, total, ratio, type, encryption, and path checks; no `extractall` |
| Dependency substitution | Exact pins and `--require-hashes`; CI vulnerability audit |
| Release tampering | Sealed whitelist, SHA-256 inventory, deterministic archive builder |
| Hidden binary/persistence | Source-only package; local scanner rejects native executable classes and legacy launchers |
| Diagnostic leakage | Summary-only crash reports; explicit sensitive opt-in; redaction |
| Stale API assumptions | Official-doc references, changelog review gate, CI and release checklist |
| Misleading profit claims | Prominent risk disclosure; arithmetic example separated from expected performance |

## Trust assumptions

- The user obtains the ZIP/hash from the owner’s authentic channels.
- Python, the operating system, certificate store, and package index are not already compromised.
- Kalshi’s documented domains, TLS certificates, API behavior, and account controls are trustworthy.
- The user protects local credentials and treats all authenticated preview output as sensitive.
- The retained engine may contain unknown defects; the boundary reduces blast radius but does not prove correctness.

## Non-goals

- Protecting a machine already controlled by malware or an administrator-level attacker.
- Guaranteeing exchange availability, fills, prices, fees, settlement, legality, or profit.
- Preventing a technically capable user from modifying the source and removing controls.
- Supporting arbitrary API mirrors, intercepting corporate proxies, or custom certificate authorities by default.
- Acting as a custody, portfolio-management, or fiduciary service.

## Residual risk

The engine remains approximately 38,000 lines and is not formally verified. Static analysis and targeted tests can find important defects but cannot exhaustively validate strategy logic, concurrent event ordering, every API response, or real-market behavior. This copy is an experimental dry-run learning preview, not a production system; order-capable work belongs in the separately reviewed 10x1c flagship.
