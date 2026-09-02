from __future__ import annotations

import sys

if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.dont_write_bytecode:
    print('PUBLIC_RELEASE_IDENTITY: FAIL')
    print('isolated_launch_required')
    print('Use the canonical BAT or run: python -I -S -B run_sell_preview.py ...')
    raise SystemExit(2)

import os
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
VERIFIER = os.path.join(ROOT, 'scripts', 'verify_release.py')


def _run_isolated(arguments: list[str]) -> int:
    completed = subprocess.run(
        [sys.executable, '-I', '-S', '-B', *arguments],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode


def main() -> int:
    verify_code = _run_isolated([VERIFIER])
    if verify_code != 0:
        return verify_code

    sys.path.append(ROOT)
    from kalshi_sell_preview.cli import main as application_main

    return application_main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
