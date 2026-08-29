# Changelog

## 41.65-public.1 — 2026-08-29

- Replaced the older v41.22.3 active preview with an offline implementation
  based on the v41.65 evidence-coherence lineage.
- Removed network, authentication, credential, and account-mutation capability.
- Added fixed 40%-at-2¢ planning, fee-gate truth, route/shard conflict quarantine,
  current-status build/age coherence, and duplicate exit-coverage checks.
- Added one canonical Python entrypoint, one thin Windows BAT shim, normalized
  manifest verification, synthetic fixtures, and standard-library-only tests.
- Hardened startup so managed-file verification completes in isolated Python
  processes before application imports; undeclared source, sourceless bytecode,
  malformed metadata paths, and extreme numeric evidence now fail closed.

Historical releases remain in Git history for transparency but are not the active
public preview.

Copyright © 2026 Gateway Information Group LLC. All rights reserved.
