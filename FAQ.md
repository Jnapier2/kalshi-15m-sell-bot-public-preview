# Frequently Asked Questions

This is an experimental advanced dry-run learning preview released under the
MIT License. `PUBLIC_PREVIEW_ONLY` permanently blocks order submission.

## Is this an official Kalshi product?

No. It is an independent project and is not affiliated with, endorsed by, or sponsored by Kalshi.

## Does it guarantee profit?

No. It can lose money, fail to fill, incur fees, or behave incorrectly. At the default 2¢ sell price, 1,000 filled contracts produce $20 in gross sale proceeds and 10,000 produce $200; net profit still depends on the existing position’s cost basis and fees. The project has no verified or promised earning rate.

## Why is demo and dry run the default?

Because the safest public default should be reversible and non-financial. Kalshi’s demo environment uses mock funds and separate credentials, although its behavior may differ from live markets.

## Can I turn dry run off?

No. `python bot.py run --live` and `python bot.py live` fail with a preview-only message. Environment variables and acknowledgment strings cannot unlock writes. Use the separately reviewed **10x1c flagship** for any order-capable workflow.

## Why keep the old live command names?

They return a clear migration message instead of silently changing behavior for someone following an older command. They do not load credentials or start the engine.

## Why can’t I store the key in the project folder?

Project folders are commonly synced, zipped, backed up, or committed. Keeping the key outside the repository reduces accidental disclosure.

## Can the bot read my account during dry run?

Yes, authenticated dry run can read account and market data so it can simulate decisions. Mutating requests are blocked before signing and network transmission.

## Does “dry run” perfectly reproduce live behavior?

No. It does not prove fill behavior, queue priority, latency, fees, or live error handling. Demo and dry-run evidence are necessary but not sufficient.

## Can I run it on macOS or Linux?

The preview launcher is cross-platform. The original project was Windows-oriented, so use demo/dry-run and report platform-specific issues.

## What license applies?

The project is available under the MIT License. Preserve the copyright and
permission notice, review the safety documentation, and verify the code in
your own environment before use. See `LICENSE.md` and `LICENSE_OPTIONS.md`.
