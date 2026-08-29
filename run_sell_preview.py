from __future__ import annotations

import sys

_TRUSTED_OS = sys.modules.get('os')
if _TRUSTED_OS is None or not hasattr(_TRUSTED_OS, 'spawnv'):
    print('PUBLIC_RELEASE_IDENTITY: FAIL')
    print('trusted_bootstrap_unavailable')
    raise SystemExit(2)

ROOT = _TRUSTED_OS.path.dirname(_TRUSTED_OS.path.abspath(__file__))
VERIFIER = _TRUSTED_OS.path.join(ROOT, 'scripts', 'verify_release.py')
APP_BOOTSTRAP = (
    "import sys; "
    "root = sys.argv[1]; "
    "args = sys.argv[2:]; "
    "sys.path.append(root); "
    "from kalshi_sell_preview.cli import main; "
    "raise SystemExit(main(args))"
)


def _run_isolated(arguments: list[str]) -> int:
    return _TRUSTED_OS.spawnv(
        _TRUSTED_OS.P_WAIT,
        sys.executable,
        [sys.executable, '-I', '-S', *arguments],
    )


def main() -> int:
    verify_code = _run_isolated([VERIFIER])
    if verify_code != 0:
        return verify_code
    return _run_isolated(['-c', APP_BOOTSTRAP, ROOT, *sys.argv[1:]])


if __name__ == '__main__':
    raise SystemExit(main())
