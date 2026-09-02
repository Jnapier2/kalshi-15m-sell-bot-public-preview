from __future__ import annotations

import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.verify_release import verify_project

ROOT = Path(__file__).resolve().parents[1]


def _copy_project(destination: Path) -> Path:
    target = destination / 'project'
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(
            '.git', '__pycache__', '*.pyc', '*.pyo',
            '.pytest_cache', '.mypy_cache', '.ruff_cache',
        ),
    )
    return target


class ReleaseIdentityTests(unittest.TestCase):
    def test_release_identity_passes(self) -> None:
        ok, errors = verify_project()
        self.assertTrue(ok, errors)

    def test_nonisolated_entrypoint_fails_closed_with_guidance(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / 'run_sell_preview.py'), '--version'],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        combined = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('isolated_launch_required', combined)

    def test_isolated_entrypoint_handles_project_path_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            spaced_parent = Path(temp) / 'project path with spaces'
            spaced_parent.mkdir()
            candidate = _copy_project(spaced_parent)
            completed = subprocess.run(
                [
                    sys.executable,
                    '-I',
                    '-S',
                    '-B',
                    str(candidate / 'run_sell_preview.py'),
                    '--version',
                ],
                cwd=Path(temp),
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            combined = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, combined)
            self.assertIn('PUBLIC_RELEASE_IDENTITY: PASS', combined)

    def test_launcher_verifies_before_importing_shadowable_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            (candidate / 'argparse.py').write_text(
                'raise RuntimeError("shadow_executed")\n',
                encoding='utf-8',
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    '-I',
                    '-S',
                    '-B',
                    str(candidate / 'run_sell_preview.py'),
                    '--version',
                ],
                cwd=candidate,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            combined = completed.stdout + completed.stderr
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('unexpected_file:argparse.py', combined)
            self.assertNotIn('shadow_executed', combined)

    def test_release_identity_rejects_unlisted_shadow_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            (candidate / 'argparse.py').write_text(
                'raise RuntimeError("shadow_executed")\n',
                encoding='utf-8',
            )
            ok, errors = verify_project(candidate)
            self.assertFalse(ok)
            self.assertIn('unexpected_file:argparse.py', errors)

    def test_release_identity_rejects_root_sourceless_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            source = candidate / 'temporary_shadow_source.py'
            source.write_text(
                'raise RuntimeError("bytecode_executed")\n',
                encoding='utf-8',
            )
            py_compile.compile(
                str(source),
                cfile=str(candidate / 'argparse.pyc'),
                doraise=True,
            )
            source.unlink()
            ok, errors = verify_project(candidate)
            self.assertFalse(ok)
            self.assertIn('unexpected_file:argparse.pyc', errors)

    def test_launcher_rejects_cache_bytecode_before_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            managed_cli = candidate / 'kalshi_sell_preview' / 'cli.py'
            original = managed_cli.read_bytes()
            original_stat = managed_cli.stat()
            payload = b'raise RuntimeError("cache_bytecode_executed")\n'
            self.assertLess(len(payload), len(original))
            replacement = payload + b'#' * (len(original) - len(payload) - 1) + b'\n'
            managed_cli.write_bytes(replacement)
            os.utime(
                managed_cli,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
            cache_dir = managed_cli.parent / '__pycache__'
            cache_dir.mkdir()
            cache_path = cache_dir / f'cli.{sys.implementation.cache_tag}.pyc'
            py_compile.compile(
                str(managed_cli),
                cfile=str(cache_path),
                doraise=True,
                invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
            )
            managed_cli.write_bytes(original)
            os.utime(
                managed_cli,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    '-I',
                    '-S',
                    '-B',
                    str(candidate / 'run_sell_preview.py'),
                    '--version',
                ],
                cwd=candidate,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            combined = completed.stdout + completed.stderr
            relative = cache_path.relative_to(candidate).as_posix()
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(f'unexpected_file:{relative}', combined)
            self.assertNotIn('cache_bytecode_executed', combined)

    def test_release_identity_rejects_non_object_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            (candidate / 'PACKAGE_METADATA.json').write_text('[]\n', encoding='utf-8')
            ok, errors = verify_project(candidate)
            self.assertFalse(ok)
            self.assertIn('metadata_not_object', errors)

    def test_release_identity_rejects_non_object_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            (candidate / 'MANIFEST.json').write_text('[]\n', encoding='utf-8')
            ok, errors = verify_project(candidate)
            self.assertFalse(ok)
            self.assertIn('manifest_not_object', errors)

    def test_release_identity_rejects_nul_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = _copy_project(Path(temp))
            manifest_path = candidate / 'MANIFEST.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest['files'][0]['path'] = 'bad\u0000path.py'
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                encoding='utf-8',
            )
            ok, errors = verify_project(candidate)
            self.assertFalse(ok)
            self.assertIn('unsafe_path_nul', errors)


if __name__ == '__main__':
    unittest.main()
