# Quick Start — Experimental Dry-Run Preview

> `PUBLIC_PREVIEW_ONLY` is permanently enabled in this MIT-licensed public copy. It cannot submit, amend, or cancel orders.

## Requirements

- Python 3.10–3.13; Python 3.11 is the recommended baseline.
- A Kalshi **demo** account and demo API key for the first run.
- A normal local folder—not a cloud-synced public folder.

## Windows

1. Clone the repository or extract the project archive into a clean folder.
2. Run `SETUP_WINDOWS.bat`.
3. Run `START_WINDOWS.bat`.
4. Choose **1 Verify**.
5. Choose **2 Configure demo credentials**.
6. Choose **3 Run one dry-run cycle**.

## macOS or Linux

```bash
./setup.sh
.venv/bin/python bot.py configure --environment demo
.venv/bin/python bot.py run
```

The configuration wizard copies the private key into private application storage outside the repository. It does not store the key contents in JSON, logs, or the project folder.

## Success signal

A safe first run should identify itself as:

```text
Mode        : DRY RUN (demo)
Duration    : one cycle
Order writes: blocked in the engine before signing or network transmission
```

The engine may then report account/authentication or market information. Fix authentication errors with a **demo key paired with the matching demo private key**. Production and demo credentials are separate.

## Continuous dry run

After one clean cycle:

```bash
python bot.py run --continuous
```

Stop with `Ctrl+C`.

## Order-capable mode is unavailable

The retained CLI names below intentionally fail closed and explain where to go:

```bash
python bot.py run --live
python bot.py live
```

No phrase or environment variable unlocks them. Use the separately reviewed **10x1c flagship** for any order-capable workflow.

## Production data in dry run

Advanced reviewers may configure production credentials to observe their own account in dry-run mode:

```bash
python bot.py configure --environment production
python bot.py run
```

This still cannot write. Use demo credentials unless production read-only evidence is specifically needed, and treat all account output as sensitive.
