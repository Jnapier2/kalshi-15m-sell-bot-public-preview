# Privacy

The public launcher stores local configuration, credentials, runtime state, logs, and exports outside the Git repository in the operating system’s application-data locations.

## Stored locally

- API Key ID (masked when displayed)
- path to the private key (not the key contents in JSON)
- selected demo/production environment
- instance name
- runtime state, operational logs, and generated reports

## Not intentionally collected

This release contains no analytics SDK, advertising SDK, telemetry service, remote support agent, updater, miner, or owner-operated collection endpoint. Network traffic is restricted to the documented Kalshi API origins unless the source is modified.

## Crash reports

Crash reports default to summary-only. Full logs, state, dashboard data, and local paths are excluded unless the operator explicitly sets `CRASH_REPORT_INCLUDE_SENSITIVE=1`. Even redacted diagnostics should be reviewed manually before sharing.

## Credentials

Never upload a private key, raw local config, authentication header, or unreviewed log/archive to GitHub, an issue, a chat, or a portfolio site. If a credential may have been exposed, revoke/rotate it through the account provider before further investigation.
