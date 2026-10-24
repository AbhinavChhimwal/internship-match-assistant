"""Recreate disposable caches, never replace durable user or catalog data."""
import threading
import hashlib
from contextlib import nullcontext
import db
from cloud_storage import StorageUnavailable, secret
from settings import ROOT

_lock = threading.Lock()
_startup_lock = threading.Lock()
_ready_key = None


def initialize_cloud(progress=nullcontext):
    """Initialize once per process/configuration, shared across browser sessions.

    Failed attempts remain retryable. No user/profile query results are cached.
    Only a configuration digest is retained; secret values are not cache keys
    exposed to Streamlit or the browser. Source reload resets this module state.
    """
    global _ready_key
    key=hashlib.sha256((secret('DATABASE_URL')+'\0'+secret('ADMIN_ACCESS_CODE')+
        '\0'+secret('SUPABASE_PROJECT_REF')+'\0'+secret('SUPABASE_MANAGEMENT_TOKEN')).encode()).digest()
    with _startup_lock:
        if _ready_key == key:
            return
        from supabase_wake import ensure_awake
        with progress():
            ensure_awake()
            db.init_db()
            prepare_catalog()
        _ready_key=key


def prepare_catalog():
    from import_jobs import read_jobs, write_jobs
    from embeddings import load_embeddings, build_embeddings
    with _lock:
        with db.connect() as con:
            con.execute('SELECT pg_advisory_xact_lock(71859302)')
            if con.execute('SELECT id FROM jobs LIMIT 1').fetchone() is None:
                write_jobs(con, read_jobs(ROOT/'data'/'jobs.csv'), replace=False)
        jobs = db.get_jobs()
        try:
            load_embeddings(jobs)
        except ValueError:
            try:
                build_embeddings(jobs)
            except Exception:
                raise StorageUnavailable('Search is still initializing. Retry shortly; the saved catalog is unchanged.') from None
