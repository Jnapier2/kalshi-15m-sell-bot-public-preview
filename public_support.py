"""Independent minimal public diagnostics; no application imports or collectors."""
import sys
if __name__ == "__main__" and not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
    print('Use: python -I -S -B public_support.py --export')
    raise SystemExit(2)
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = '41.90-public.1'
BUILD = 'KALSELL-PUBLIC-41.90.1-COST-REVIEW'
PACKAGE_ID = 'KALSHI_15M_SELL_BOT_PUBLIC_PREVIEW'
RUN_ID = uuid.uuid4().hex
_SEEN_CRITICAL = False
MAX_EXPORTS = 64
MAX_BYTES = 32768


def safe_folder():
    folder = ROOT
    for part in ('outputs', 'support'):
        folder = folder / part
        if folder.is_symlink() or (hasattr(folder, 'is_junction') and folder.is_junction()):
            raise ValueError('UNSAFE_OUTPUT')
        folder.mkdir(exist_ok=True)
        if not folder.is_dir() or folder.resolve().is_relative_to(ROOT) is not True:
            raise ValueError('UNSAFE_OUTPUT')
    if shutil.disk_usage(folder).free < 1048576:
        raise ValueError('INSUFFICIENT_SPACE')
    return folder


def atomic_write(path, raw):
    if len(raw) > MAX_BYTES or path.is_symlink():
        raise ValueError('OUTPUT_REJECTED')
    stage = path.parent / ('.stage-' + uuid.uuid4().hex)
    try:
        with stage.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(stage, path)
    finally:
        if stage.exists() and not stage.is_symlink():
            stage.unlink()


def export_support(status='NOT_CHECKED'):
    """Four generated records, no user content. A capsule precedes Critical ZIPs.

    Numeric bounds limit work and disk growth; OS filesystem stalls are not a hard
    real-time guarantee. No logs, inputs, source, environment or network are read.
    """
    global _SEEN_CRITICAL
    if status not in {'PASS', 'FAIL', 'NOT_CHECKED'}:
        return {'status': 'ERROR', 'code': 'INVALID_REQUEST'}
    if status == 'FAIL' and _SEEN_CRITICAL:
        return {'status': 'SUPPRESSED', 'code': 'CRITICAL_ALREADY_CAPTURED'}
    started = time.monotonic()
    capsule = None
    lock = None
    folder = None
    try:
        folder = safe_folder()
        lockpath = folder / '.export.lock'
        lock = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        # Bounded exporter-owned bookkeeping only. Never scan or prune user files.
        counter = folder / '.export_count'
        count = 0
        if counter.exists() or counter.is_symlink():
            if counter.is_symlink() or not stat.S_ISREG(counter.lstat().st_mode) or counter.stat().st_size > 4:
                raise ValueError('COUNTER_REJECTED')
            count = int(counter.read_text(encoding='ascii'))
        if not 0 <= count < MAX_EXPORTS:
            raise ValueError('EXPORT_BUDGET_REACHED')
        atomic_write(counter, str(count + 1).encode('ascii'))
        export_id = uuid.uuid4().hex
        identity = {'schema': 'public-export20-v2', 'package_id': PACKAGE_ID,
                    'version': VERSION, 'build_id': BUILD, 'integrity': status,
                    'run_id': RUN_ID, 'export_id': export_id, 'file_count': 4,
                    'network_access': False, 'input_collected': False}
        evidence = {'mode': 'OFFLINE_ONLY', 'application_health': 'NOT_CHECKED',
                    'integrity': status, 'trigger': 'PACKAGE_INTEGRITY_FAILURE' if status == 'FAIL' else 'MANUAL',
                    'last_successful_stage': 'TRUSTED_SUPPORT',
                    'failed_stage': 'PACKAGE_VERIFICATION' if status == 'FAIL' else None,
                    'original_exit_code': 2 if status == 'FAIL' else None,
                    'collector_scope': 'FIXED_SAFE_FIELDS_ONLY',
                    'unavailable': ['private_runtime', 'account_state', 'Norton', 'publisher_signature']}
        if status == 'FAIL':
            capsule = folder / ('Critical_' + export_id + '.json')
            atomic_write(capsule, (json.dumps({'identity': identity, 'evidence': evidence}, sort_keys=True) + '\n').encode())
            _SEEN_CRITICAL = True
        entries = {
            'identity.json': json.dumps(identity, sort_keys=True) + '\n',
            'diagnostics.json': json.dumps(evidence, sort_keys=True) + '\n',
            'PRIVACY.txt': 'No input snapshots, account records, logs, source, environment or personal paths collected.\n',
            'README.txt': 'Minimal public diagnostics only. NOT_CHECKED is not PASS. Restore an independently verified public package; preserve user data. No automatic repair is attempted.\n'
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, value in entries.items():
                archive.writestr(name, value)
        raw = buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if archive.testzip() is not None or len(archive.infolist()) != 4:
                raise ValueError('ARCHIVE_REJECTED')
        if time.monotonic() - started > 2 or len(raw) > MAX_BYTES:
            raise ValueError('EXPORT_BUDGET_REACHED')
        destination = folder / ('Export20_' + export_id + '.zip')
        atomic_write(destination, raw)
        return {'status': 'EXPORTED', 'coverage': 'MINIMAL_PUBLIC_DIAGNOSTICS',
                'path': destination.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(),
                'capsule': capsule.relative_to(ROOT).as_posix() if capsule else None, 'file_count': 4}
    except Exception:
        if capsule and capsule.is_file() and not capsule.is_symlink():
            return {'status': 'CAPSULE_ONLY', 'code': 'EXPORT_FAILED', 'path': capsule.relative_to(ROOT).as_posix()}
        return {'status': 'ERROR', 'code': 'EXPORT_FAILED'}
    finally:
        if lock is not None:
            os.close(lock)
            try:
                (folder / '.export.lock').unlink()
            except OSError:
                pass


if __name__ == '__main__':
    result = export_support() if sys.argv[1:] in ([], ['--export']) else {'status': 'ERROR', 'code': 'INVALID_REQUEST'}
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['status'] == 'EXPORTED' else 2)
