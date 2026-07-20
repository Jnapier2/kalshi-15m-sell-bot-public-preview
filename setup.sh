#!/usr/bin/env sh
set -eu

cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.10-3.13 is required." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if not ((3, 10) <= sys.version_info[:2] < (3, 14)):
    raise SystemExit("Python 3.10-3.13 is required.")
PY

# These two checks use only Python's standard library and run before any package installation.
"$PYTHON_BIN" scripts/verify_release.py
"$PYTHON_BIN" scripts/security_check.py --root .

"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip --isolated install \
  --disable-pip-version-check \
  --no-input \
  --only-binary=:all: \
  --require-hashes \
  -r requirements.lock.txt
.venv/bin/python bot.py verify

echo
echo "Setup complete. Next: .venv/bin/python bot.py configure"
