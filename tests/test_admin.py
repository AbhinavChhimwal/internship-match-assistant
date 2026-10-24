import csv
from datetime import date
from pathlib import Path
import json
import numpy as np
import pytest
import db
import catalog_admin
import embeddings
from catalog_admin import add_job,create_admin,require_admin,csv_record
from import_jobs import import_jobs,read_jobs
from schemas import Job,Profile
from search import search_jobs

def fixture_job(url='https://example.org/custom-intern'):
    return Job(source_url=url,title='Custom Python Intern',company='Fixture Company',
        description='Build Python APIs and SQL queries for this synthetic test role.',
        required_skills=['python','sql'],work_mode='remote',location='India',
        compatible_locations=['india'],eligible_graduation_years=[2028],
        last_checked_at=date.today(),is_active=True)

def seed_csv(path):
    job=fixture_job('https://example.org/seed')
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(csv_record(job)))
        writer.writeheader();writer.writerow(csv_record(job))

def test_student_cannot_write_catalog(database,tmp_path):
    path,uid,_=database
    target=tmp_path/'jobs.csv';seed_csv(target)
    before=target.read_bytes()
    with pytest.raises(PermissionError):
        add_job(uid,fixture_job(),csv_path=target,path=path)
    assert target.read_bytes()==before

def test_admin_add_updates_csv_db_and_vectors(database,tmp_path,monkeypatch):
    path,_,_=database
    code=create_admin(path=path)
    admin=db.authenticate(code,path)
    assert admin['is_admin']==1
    target=tmp_path/'jobs.csv';seed_csv(target)
    import_jobs(target,path)
    original_id=db.get_jobs(path)[0]['id']
    class Encoder:
        def encode(self,texts,**kwargs):return np.ones((len(texts),4),dtype=np.float32)/2
    monkeypatch.setattr(embeddings,'load_model',lambda: Encoder())
    result=add_job(admin['id'],fixture_job(),csv_path=target,path=path,directory=tmp_path/'index')
    assert result=={'count':2,'indexed':True}
    assert len(read_jobs(target))==2
    jobs=db.get_jobs(path)
    assert jobs[0]['id']==original_id
    assert len(embeddings.load_embeddings(jobs,tmp_path/'index'))==2
    with pytest.raises(ValueError,match='already exists'):
        add_job(admin['id'],fixture_job(),csv_path=target,path=path)
    assert len(read_jobs(target))==2

def test_failed_index_does_not_lose_saved_job(database,tmp_path):
    path,_,_=database
    admin=db.authenticate(create_admin(path=path),path)
    target=tmp_path/'jobs.csv';seed_csv(target)
    def failed(*a):raise OSError('model unavailable')
    result=add_job(admin['id'],fixture_job(),csv_path=target,path=path,indexer=failed)
    assert not result['indexed'] and len(read_jobs(target))==2
    assert len(db.get_jobs(path))==2

def test_database_import_failure_restores_csv(database,tmp_path,monkeypatch):
    path,_,_=database
    uid=db.authenticate(create_admin(path=path),path)['id']
    target=tmp_path/'jobs.csv';seed_csv(target)
    before=read_jobs(target)
    def failed(*args):raise OSError('database unavailable')
    monkeypatch.setattr(catalog_admin,'import_jobs',failed)
    with pytest.raises(OSError):
        add_job(uid,fixture_job(),csv_path=target,path=path)
    assert [j.model_dump(mode='json') for j in read_jobs(target)]==[j.model_dump(mode='json') for j in before]

def test_opt_in_unknown_year_is_explicit_and_preserves_other_filters(job,database):
    path,uid,_=database
    jobs=[{**job,'eligible_graduation_years':None},
        {**job,'id':2,'eligible_graduation_years':[2027]},
        {**job,'id':3,'eligible_graduation_years':None,'work_mode':'onsite'}]
    profile=Profile(remote_only=True,preferred_locations=['india'])
    assert not search_jobs(jobs,profile,method='keyword')['results']
    profile.allow_unknown_graduation=True
    db.save_profile(uid,profile,path)
    restored=db.get_profile(uid,path)
    assert restored.allow_unknown_graduation
    result=search_jobs(jobs,restored,method='keyword')
    assert [j['id'] for j in result['results']]==[1]

def test_one_hundred_new_real_source_records():
    additions=json.loads(Path('data/web_additions_2026-10-24.json').read_text(encoding='utf-8'))
    assert len(additions)==100
    urls={str(Job.model_validate(row).source_url) for row in additions}
    assert len(urls)==100
    assert urls.issubset({str(j.source_url) for j in read_jobs('data/jobs.csv')})
    assert all('example.' not in url for url in urls)
