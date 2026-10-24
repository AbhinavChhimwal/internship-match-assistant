"""Explicit manual CSV import. Never fetches or scrapes job listings."""
import argparse
import json
import pandas as pd
from db import connect, init_db
from schemas import Job

def read_jobs(csv_path):
    frame=pd.read_csv(csv_path,keep_default_na=False,dtype=str)
    rows=[]
    for index, raw in enumerate(frame.to_dict('records'),start=2):
        try:
            for key in ('required_skills','eligible_graduation_years','compatible_locations'):
                raw[key]=json.loads(raw.get(key) or 'null')
            for key in ('location','work_mode'):
                raw[key]=raw.get(key) or None
            if raw['is_active'].lower() not in ('true','false'):
                raise ValueError('is_active must be true or false')
            raw['is_active']=raw['is_active'].lower()=='true'
            rows.append(Job.model_validate(raw))
        except (ValueError,KeyError) as error:
            raise ValueError(f'CSV row {index}: {error}') from error
    urls=[str(j.source_url) for j in rows]
    if len(set(urls)) != len(urls):
        raise ValueError('Duplicate source URLs: deduplicate before importing')
    return rows

def import_jobs(csv_path,path=None):
    jobs=read_jobs(csv_path)  # Validate whole file before changing anything.
    if not jobs:
        raise ValueError('Refusing an empty import')
    init_db(path)
    with connect(path) as con:
        write_jobs(con,jobs)
    return len(jobs)

def write_jobs(con,jobs,replace=True):
    if replace:
        con.execute('UPDATE jobs SET is_active=0')
    for job in jobs:
        data=job.model_dump(mode='json')
        text=f"Role: {job.title}. Skills: {', '.join(job.required_skills or [])}. Responsibilities: {job.description}"
        values=(str(job.source_url),job.title,job.company,job.description,
            json.dumps(job.required_skills),job.work_mode,job.location,
            json.dumps(job.eligible_graduation_years),data['last_checked_at'],int(job.is_active),
            json.dumps(job.compatible_locations),text)
        con.execute('''INSERT INTO jobs(source_url,title,company,description,required_skills_json,
            work_mode,location,eligible_graduation_years_json,last_checked_at,is_active,
            compatible_locations_json,embedding_text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_url) DO UPDATE SET title=excluded.title,company=excluded.company,
            description=excluded.description,required_skills_json=excluded.required_skills_json,
            work_mode=excluded.work_mode,location=excluded.location,
            eligible_graduation_years_json=excluded.eligible_graduation_years_json,
            last_checked_at=excluded.last_checked_at,is_active=excluded.is_active,
            compatible_locations_json=excluded.compatible_locations_json,embedding_text=excluded.embedding_text''',values)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('csv',nargs='?',default='data/jobs.csv')
    args=parser.parse_args()
    print(f'Imported {import_jobs(args.csv)} jobs. Now run: python embeddings.py')
