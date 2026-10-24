import json
import numpy as np
import pytest
import db
from import_jobs import import_jobs, read_jobs
from embeddings import fingerprint, load_embeddings
from settings import MODEL_NAME

def test_curated_dataset_valid_and_stable_ids(database):
    path,uid,_=database
    assert len(read_jobs('data/jobs.csv'))>=50
    import_jobs('data/jobs.csv',path)
    before={j['source_url']:j['id'] for j in db.get_jobs(path)}
    db.set_feedback(uid,next(iter(before.values())),'saved',path)
    import_jobs('data/jobs.csv',path)
    assert {j['source_url']:j['id'] for j in db.get_jobs(path)}==before
    assert db.get_feedback(uid,path)
    with db.connect(path) as con:
        assert len(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())==4

def test_id_alignment_and_stale_rejection(tmp_path,job):
    jobs=[job,{**job,'id':2,'embedding_text':'Different'}]
    np.save(tmp_path/'job_embeddings.npy',np.array([[0,1],[1,0]]))
    (tmp_path/'job_ids.json').write_text('[2,1]')
    (tmp_path/'embedding_manifest.json').write_text(json.dumps({'model':MODEL_NAME,'fingerprint':fingerprint(jobs)}))
    vectors=load_embeddings(jobs,tmp_path)
    assert vectors[1].tolist()==[1,0]
    jobs[0]['embedding_text']='Revised'
    with pytest.raises(ValueError,match='stale'):
        load_embeddings(jobs,tmp_path)
