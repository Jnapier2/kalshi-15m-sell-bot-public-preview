# Publication Blockers — Preview Only

> **Do not publish this preview.** It is an experimental hard-blocked dry-run learning artifact with unresolved licensing and review gates. The checklist records prerequisites; it is not authorization to release.

## Hard gates

- [ ] **Choose and install a license.** Replace the placeholder `LICENSE.md`; obtain legal review if appropriate.
- [ ] Confirm you own or have permission to publish every retained source file.
- [ ] Run `python bot.py verify` from a clean extraction.
- [ ] Run the deep maintainer checks in `SECURITY_AUDIT.md`.
- [ ] Confirm no API key, private key, `.env`, local config, state, log, export, screenshot, or account identifier exists in Git history.
- [ ] Rotate any credential that was ever committed, even if later deleted.
- [ ] Publish the release ZIP SHA-256 separately from the ZIP.
- [ ] Test the exact final ZIP after downloading it from the public release page.
- [ ] Enable GitHub secret scanning/push protection where available, CodeQL, dependency review, and Dependabot.
- [ ] Pin every third-party GitHub Action to a reviewed full commit SHA before a high-assurance release.
- [ ] Enable GitHub private vulnerability reporting, then add the repository-specific advisory link to `.github/ISSUE_TEMPLATE/config.yml`.
- [ ] Confirm the README disclaimer and non-affiliation statement remain visible.

## Repository presentation

- [ ] Add a short demo video or GIF using only demo/mock data.
- [ ] Add one architecture image derived from `docs/ARCHITECTURE.md`.
- [ ] After every legal and technical gate is independently approved, define a new reviewed version rather than tagging this preview.
- [ ] Add topics from `PORTFOLIO_COPY.md`.
- [ ] Keep portfolio references labeled as a private experimental preview until publication is separately approved.
- [ ] Keep screenshots free of usernames, paths, balances, order IDs, and credentials.
- [ ] Rewrite and approve external copy from scratch; `LINKEDIN_POST.md` is a private draft, not ready-to-post launch copy.

## Operational maintenance

- [ ] Review Kalshi API changelog and rate-limit documentation before each release.
- [ ] Regenerate hash locks and run `pip-audit` when dependencies change.
- [ ] Re-run demo smoke tests after API, authentication, fee, order-schema, or WebSocket changes.
- [ ] Document every safety-affecting change in `CHANGELOG.md`.
- [ ] Never remove or weaken `PUBLIC_PREVIEW_ONLY`, fixed dry run, or the final mutation block in this preview.
