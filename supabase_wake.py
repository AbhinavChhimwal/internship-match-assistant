"""Bounded server-side resume of a paused project; never logs credentials."""
import json
import re
import threading
import time
from urllib.request import Request, urlopen
from cloud_storage import secret, StorageUnavailable

_lock = threading.Lock()
_checked_at = 0.0
_restore_requested_at = 0.0


def management_request(ref, token, method='GET', opener=urlopen):
    suffix = '/restore' if method == 'POST' else ''
    request = Request(f'https://api.supabase.com/v1/projects/{ref}{suffix}',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        data=b'{}' if method == 'POST' else None, method=method)
    try:
        with opener(request, timeout=15) as response:
            return json.loads(response.read() or b'{}')
    except Exception:
        raise StorageUnavailable('Could not check or resume Supabase. Check the project and management token privately in Settings.') from None


def ensure_awake(notify=lambda message: None, request=management_request,
                 sleep=time.sleep, clock=time.monotonic, timeout=45):
    global _checked_at, _restore_requested_at
    ref, token = secret('SUPABASE_PROJECT_REF'), secret('SUPABASE_MANAGEMENT_TOKEN')
    if not token:
        return  # Manual restoration remains available without a management token.
    if not re.fullmatch(r'[a-z0-9]{20}', ref):
        raise StorageUnavailable('Set SUPABASE_PROJECT_REF to the project reference from Supabase Settings.')
    with _lock:
        if _checked_at and clock() - _checked_at < 60:
            return
        deadline = clock() + timeout
        while True:
            status = request(ref, token).get('status')
            if status == 'ACTIVE_HEALTHY':
                _checked_at = clock()
                return
            if status == 'INACTIVE':
                if not _restore_requested_at or clock() - _restore_requested_at > 120:
                    request(ref, token, 'POST')
                    _restore_requested_at = clock()
                notify('Starting the database. Please wait…')
            elif status in ('COMING_UP', 'RESTORING', 'ACTIVE_UNHEALTHY', 'GOING_DOWN'):
                notify('Starting the database. Please wait…')
            else:
                raise StorageUnavailable('Supabase needs attention. Open its dashboard to check the project status.')
            if clock() >= deadline:
                raise StorageUnavailable('The database is still starting. Please retry shortly. Your stored data has not been reset.')
            sleep(3)
