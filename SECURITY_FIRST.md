# Security First: Verify Before You Trust

Do this **before entering an API Key ID or copying a private key**. This
MIT-licensed public preview has no order-capable mode.

## 1. Confirm a packaged archive hash

When a release provides both a project ZIP and a separately published SHA-256
value, calculate the downloaded file's hash and compare every character.
GitHub's automatically generated source archives are not sealed project
releases and do not include a project-issued sidecar; cloned source can proceed
to the repository inventory check in step 2.

Windows PowerShell:

```powershell
Get-FileHash .\kalshi-15m-sell-bot-public-v41.22.2.zip -Algorithm SHA256
```

macOS or Linux:

```bash
sha256sum kalshi-15m-sell-bot-public-v41.22.2.zip
```

A mismatch means: stop, delete the copy, and obtain it again from the official repository or release channel.

## 2. Verify the extracted inventory without installing anything

```bash
python scripts/verify_release.py
```

Expected signal:

```text
[PASS] Release integrity and inventory verified (... files)
```

This rejects changed, missing, extra, bytecode, or symlinked release files.

## 3. Run the source safety gate

```bash
python scripts/security_check.py --root .
```

This scans for credential files, private-key material, native executables, bytecode, symlinks, dangerous Python calls, unexpected executable-code URLs, missing safety markers, non-sell order-create protections, weak dependency records, and the retired live-first launchers.

## 4. Install only hash-locked dependencies

Use the supplied setup script. It calls pip with `--require-hashes`, so an altered or substituted dependency archive is rejected.

Windows:

```text
SETUP_WINDOWS.bat
```

macOS or Linux:

```bash
./setup.sh
```

Then run the complete local gate:

```bash
.venv/bin/python bot.py verify       # macOS/Linux
.venv\Scripts\python.exe bot.py verify  # Windows
```

## 5. Review the safety posture

A safe first-run copy should show all of these:

- Endpoint: `https://external-api.demo.kalshi.co/trade-api/v2`
- Mode: dry run
- Duration: one cycle
- Proxy use: disabled
- Order writes: blocked before signing/network transmission
- Public scope: sell-only; buy planning is disabled and non-sell creates fail before signing
- Key file: outside the project folder
- Runtime state/logs/exports: outside the project folder

Run:

```bash
python bot.py status
```

The command masks the API Key ID and shows only the key filename—not its contents or full path.

## 6. Use demo credentials first

Kalshi’s official documentation says the demo environment uses mock funds, has separate credentials from production, and may not behave like real markets. Configure demo first:

```bash
python bot.py configure --environment demo
python bot.py run
```

## 7. Confirm the immutable preview lock

The supported command is `python bot.py run`, which keeps order writes blocked. These legacy forms deliberately fail:

```bash
python bot.py run --live
python bot.py live
```

`PUBLIC_PREVIEW_ONLY=True` is a literal source sentinel enforced by the launcher, engine startup, and final pre-signing mutation boundary. `DRY_RUN` and `FORCE_LIVE_RUN` environment values cannot override it. Use the separately reviewed **10x1c flagship** for any order-capable workflow.

## 8. Understand what “PASS” does and does not mean

A passing gate establishes that:

- this copy matches the sealed release inventory;
- the included source controls and tests are present and pass locally;
- no known credential file or native executable is included;
- the hard preview-only mutation block is present.

It does **not** establish that:

- the strategy will make money;
- every possible vulnerability or defect has been found;
- your operating system, Python installation, network, account, or dependencies are uncompromised;
- the bot is suitable for your financial situation or legal jurisdiction;
- a future Kalshi API or market-rule change will preserve behavior.

## Red flags: stop immediately

Do not continue if the copy asks you to:

- disable antivirus, firewall, TLS verification, browser protection, or SmartScreen;
- place a private key inside the Git repository;
- send credentials to a non-Kalshi domain;
- install an unlisted executable, browser extension, driver, miner, or remote-access tool;
- edit or bypass the preview-only sentinel to enable trading;
- believe that profit is guaranteed.

## Reporting a security issue

Follow [SECURITY.md](SECURITY.md). Do not open a public issue containing credentials, private keys, account identifiers, order details, or unredacted logs.
