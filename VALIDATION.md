# Validation — 41.84-public.1

Local qualification on 2026-09-18: 58/58 deterministic unittest cases passed under Python 3.13.5 on Linux. The original private bot code was not executed.

Critical checks: synthetic-only strict schema; scope and route contradictions; incomplete and stale evidence; ambiguous intent and duplicate-ID rejection; fixed quantity/price or cumulative-target arithmetic; fee and funding gates; no transport or credential imports in runtime; managed-file tamper/missing/extra-file rejection before planner imports.

High checks: isolated/no-site/no-bytecode startup; unrelated-working-directory invocation; input size and duplicate-key limits; four-file independent Export20 even when the manifest and planner are missing; privacy-by-construction exports; visible bounded export failure; grouped-menu EOF exit. Python source parses. All three fixture files are explicitly synthetic.

Normal checks: 27 shipped regular files; exactly one main BAT and one independent export BAT; preserved namespace and public title; MIT and third-party notices retained; manifest and metadata agree. Public payload receives a pattern scan for key material, token-shaped credentials, email addresses, private IPv4 addresses, and user-specific Windows paths. Pattern scanning is a heuristic, not a guarantee or antivirus clearance.

The final ZIP is re-extracted and the same tests and manifest verification are rerun against those exact bytes. The ZIP CRC and deterministic rebuild are checked in the external publication receipt. This document does not claim it can include its own final archive checksum.

Not run locally: native Windows BAT execution, antivirus review, publisher signing, real exchange behavior, financial performance, or exhaustive historical-repository scanning. CI results are separate commit-bound evidence and must be read from GitHub Actions; no pending check is claimed as passed.

Copyright © 2026 Gateway Information Group LLC. All rights reserved.
