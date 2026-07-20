# Third-Party Notices

This project depends on third-party Python packages. Their own copyright, license, attribution, and data-notice terms apply; the project owner’s notice does not replace them.

Direct runtime dependencies:

- Requests — Apache License 2.0; preserve its bundled NOTICE.
- certifi — Mozilla Public License 2.0; its CA bundle includes upstream certificate notices.
- cryptography — Apache License 2.0 **or** BSD 3-Clause, as published by the project.
- websockets — BSD 3-Clause.
- tzdata — Apache License 2.0 for the Python package; preserve the package’s bundled notices for the underlying time-zone data.

Transitive dependencies and declared license expressions are listed in `requirements.lock.txt` and `SBOM.cdx.json`. When redistributing, use the exact installed distributions or their official source records to collect complete license and NOTICE text. Regenerate the lock files, SBOM, and this notice whenever dependencies change.
