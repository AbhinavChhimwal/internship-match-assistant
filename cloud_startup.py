"""Recreate disposable caches, never replace durable user or catalog data."""
import threading
import db
from cloud_storage import StorageUnavailable
from settings import ROOT

_lock = threading.Lock()


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
