"""Authenticated manual catalog editing. The CSV remains the source of truth."""
import csv
import json
import os
from pathlib import Path
import tempfile
import threading
import db
import cloud_storage
from embeddings import build_embeddings
from import_jobs import read_jobs,import_jobs,write_jobs
from schemas import Job
from settings import ROOT

_catalog_lock=threading.RLock()
CSV_PATH=ROOT/'data'/'jobs.csv'

def require_admin(uid,path=None):
    user=db.get_user(uid,path)
    if not user or not user.get('is_admin'):
        raise PermissionError('Administrator access required.')

def create_admin(name='Admin',path=None):
    db.init_db(path)
    code=db.create_user(name,path)
    user=db.authenticate(code,path)
    with db.connect(path) as con:
        con.execute('UPDATE users SET is_admin=1 WHERE id=?',(user['id'],))
    return code

def csv_record(job):
    record=job.model_dump(mode='json')
    for key in ('required_skills','eligible_graduation_years','compatible_locations'):
        record[key]=json.dumps(record[key])
    for key in ('work_mode','location'):
        record[key]=record[key] or ''
    record['is_active']=str(record['is_active']).lower()
    return record

def _write_csv(target,jobs):
    target=Path(target)
    handle=tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='',suffix='.csv',
        prefix='.catalog-',dir=target.parent,delete=False)
    temporary=Path(handle.name)
    try:
        with handle:
            writer=csv.DictWriter(handle,fieldnames=list(csv_record(jobs[0])))
            writer.writeheader()
            writer.writerows(csv_record(job) for job in jobs)
        read_jobs(temporary)
        os.replace(temporary,target)
    finally:
        temporary.unlink(missing_ok=True)

def add_job(uid,job,csv_path=None,path=None,directory=None,indexer=None):
    require_admin(uid,path)
    job=Job.model_validate(job.model_dump() if hasattr(job,'model_dump') else job)
    if cloud_storage.enabled(path):
        with db.connect(path) as con:
            con.execute('SELECT pg_advisory_xact_lock(71859302)')
            if con.execute('SELECT id FROM jobs WHERE source_url=?',(str(job.source_url),)).fetchone():
                raise ValueError('A listing with this source URL already exists.')
            write_jobs(con,[job],replace=False)
        jobs=db.get_jobs(path)
        try:
            (indexer or build_embeddings)(jobs,directory)
            indexed=True
        except Exception:
            indexed=False
        return {'count':len(jobs),'indexed':indexed}
    target=Path(csv_path or CSV_PATH)
    with _catalog_lock:
        original=read_jobs(target)
        if str(job.source_url) in {str(j.source_url) for j in original}:
            raise ValueError('A listing with this source URL already exists.')
        _write_csv(target,[*original,job])
        try:
            count=import_jobs(target,path)
        except Exception:
            _write_csv(target,original)
            raise
        try:
            (indexer or build_embeddings)(db.get_jobs(path),directory)
            indexed=True
        except Exception:
            indexed=False
        return {'count':count,'indexed':indexed}

def rebuild_index(uid,path=None,directory=None):
    require_admin(uid,path)
    with _catalog_lock:
        return build_embeddings(db.get_jobs(path),directory)


def export_catalog(uid,path=None):
    """Download the durable catalog, including cloud additions after restarts."""
    import io
    require_admin(uid,path)
    output=io.StringIO(newline='')
    jobs=[Job.model_validate({k:j[k] for k in Job.model_fields}) for j in db.get_jobs(path)]
    if not jobs:
        return b''
    writer=csv.DictWriter(output,fieldnames=list(csv_record(jobs[0])))
    writer.writeheader()
    writer.writerows(csv_record(j) for j in jobs)
    return output.getvalue().encode('utf-8')
