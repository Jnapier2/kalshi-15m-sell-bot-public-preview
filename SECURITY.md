# Security Policy

## Supported version

Security fixes are accepted for the current MIT-licensed public preview. Older
copies should be retired in favor of the latest verified release.

## Private reporting

Report suspected vulnerabilities privately to the repository owner using GitHub's private vulnerability-reporting feature through the repository Security tab. Include:

- affected version and SHA-256;
- operating system and Python version;
- concise reproduction steps using demo/dry-run when possible;
- expected and observed behavior;
- sanitized logs or screenshots;
- whether credentials, money, or account state may have been exposed.

Do not include private keys, full API Key IDs, signatures, raw authentication headers, unredacted account identifiers, or live order details.

## Response priorities

Credential exfiltration, unauthorized order submission, arbitrary code execution, path traversal, unsafe archive extraction, signature/authentication bypass, and secret leakage are treated as critical.

## Security boundaries

The preview protects four primary boundaries:

1. **Network destination:** authenticated requests are restricted to exact official Kalshi demo/production origins; redirects and system proxies are disabled by default.
2. **Immutable no-write control:** `PUBLIC_PREVIEW_ONLY=True`, fixed `DRY_RUN=True`, blocked legacy live CLI paths, and a final pre-signing mutation rejection make this copy non-order-capable.
3. **Credential/storage isolation:** private keys, config, logs, state, and exports remain outside the repository.
4. **Release/supply chain:** every retained file is inventoried and hashed; dependencies are exact-version and hash locked; CI runs additional analysis.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for assumptions and non-goals.

## Disclosure expectations

Please allow the owner a reasonable opportunity to reproduce, contain, fix, and release an update before public disclosure. This request does not authorize access to another person’s account, credentials, computer, or data; destructive testing; live-market disruption; social engineering; or denial-of-service activity.
