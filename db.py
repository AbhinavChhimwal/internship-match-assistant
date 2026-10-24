"""Four tables; all user-scoped queries use bound parameters."""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from schemas import Profile, PreferenceArgs, preference_skills
from settings import STATE_DIR
import cloud_storage

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect(path=None):
    if cloud_storage.enabled(path):
        con = cloud_storage.open_postgres()
        try:
            with con:
                yield cloud_storage.PostgresConnection(con)
        except cloud_storage.StorageUnavailable:
            raise
        except Exception:
            # Provider errors can include credentials, uploaded data or SQL parameters.
            raise cloud_storage.StorageUnavailable('Cloud database operation failed. Check its availability and configuration.') from None
        return
    target = Path(path) if path else STATE_DIR / 'matcher.db'
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

def init_db(path=None):
    with connect(path) as con:
        cloud = cloud_storage.enabled(path)
        if cloud:
            con.execute('SELECT pg_advisory_xact_lock(71859301)')
            con.execute('CREATE SCHEMA IF NOT EXISTS internship_match')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, display_name TEXT NOT NULL,
          access_token_hash TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS profiles (
          user_id INTEGER PRIMARY KEY REFERENCES users(id), skills_json TEXT NOT NULL,
          interests TEXT NOT NULL, graduation_year INTEGER NOT NULL,
          remote_only INTEGER NOT NULL CHECK(remote_only IN (0,1)),
          preferred_locations_json TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY, source_url TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
          company TEXT NOT NULL, description TEXT NOT NULL, required_skills_json TEXT,
          work_mode TEXT, location TEXT, eligible_graduation_years_json TEXT,
          last_checked_at TEXT NOT NULL, is_active INTEGER NOT NULL CHECK(is_active IN (0,1)),
          compatible_locations_json TEXT, embedding_text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS feedback (
          user_id INTEGER NOT NULL REFERENCES users(id), job_id INTEGER NOT NULL REFERENCES jobs(id),
          action TEXT NOT NULL CHECK(action IN ('saved','hidden')), created_at TEXT NOT NULL,
          UNIQUE(user_id, job_id));
        ''')
        if not cloud:
            con.execute('BEGIN IMMEDIATE')
        def columns(table):
            if cloud:
                return {r['column_name'] for r in con.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='internship_match' AND table_name=?", (table,))}
            return {r['name'] for r in con.execute(f'PRAGMA table_info({table})')}
        user_columns=columns('users')
        if 'is_admin' not in user_columns:
            con.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))')
        existing=columns('profiles')
        for name,kind in (('resume_name','TEXT'),('resume_mime','TEXT'),('resume_data','BLOB'),
                          ('resume_uploaded_at','TEXT'),('resume_skills_json','TEXT'),
                          ('allow_unknown_graduation','INTEGER NOT NULL DEFAULT 0')):
            if name not in existing:
                con.execute(f'ALTER TABLE profiles ADD COLUMN {name} {"BYTEA" if cloud and kind=="BLOB" else kind}')
        if cloud:
            for table in ('users','profiles','jobs','feedback'):
                con.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        # Public demonstration account; never grant administrator permissions.
        demo_hash = hashlib.sha256(b'DUMMY').hexdigest()
        con.execute('INSERT OR IGNORE INTO users(display_name,access_token_hash,is_admin) VALUES (?,?,0)',
                    ('DUMMY', demo_hash))
        demo = con.execute('SELECT id FROM users WHERE access_token_hash=?', (demo_hash,)).fetchone()
        con.execute('UPDATE users SET is_admin=0 WHERE id=?', (demo['id'],))
        profile = Profile()
        con.execute('''INSERT OR IGNORE INTO profiles(user_id,skills_json,interests,graduation_year,
          remote_only,preferred_locations_json,updated_at,allow_unknown_graduation)
          VALUES (?,?,?,?,?,?,?,?)''',
          (demo['id'],json.dumps(profile.skills),profile.interests,profile.graduation_year,
           int(profile.remote_only),json.dumps(profile.preferred_locations),now(),
           int(profile.allow_unknown_graduation)))
        if cloud:
            admin_code=cloud_storage.secret('ADMIN_ACCESS_CODE').strip()
            if len(admin_code)<24 or admin_code.startswith(('replace-','your-','paste-')):
                raise cloud_storage.StorageUnavailable('Set a private ADMIN_ACCESS_CODE of at least 24 characters in Streamlit Secrets.')
            admin_hash=hashlib.sha256(admin_code.encode()).hexdigest()
            con.execute('''INSERT INTO users(display_name,access_token_hash,is_admin) VALUES (?,?,1)
                ON CONFLICT(access_token_hash) DO UPDATE SET is_admin=1''', ('Admin',admin_hash))

def create_user(name, path=None):
    token = secrets.token_urlsafe(24)
    with connect(path) as con:
        uid = con.execute('INSERT INTO users(display_name,access_token_hash) VALUES (?,?) RETURNING id',
                          (name, hashlib.sha256(token.encode()).hexdigest())).fetchone()['id']
    save_profile(uid, Profile(), path)
    return token

def authenticate(token, path=None):
    with connect(path) as con:
        row = con.execute('SELECT id,display_name,is_admin FROM users WHERE access_token_hash=?',
                          (hashlib.sha256(token.strip().encode()).hexdigest(),)).fetchone()
    return dict(row) if row else None

def save_profile(uid, profile, path=None):
    profile = Profile.model_validate(profile.model_dump())
    with connect(path) as con:
        con.execute('''INSERT INTO profiles(user_id,skills_json,interests,graduation_year,remote_only,
          preferred_locations_json,updated_at,allow_unknown_graduation) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
          skills_json=excluded.skills_json,interests=excluded.interests,
          graduation_year=excluded.graduation_year,remote_only=excluded.remote_only,
          preferred_locations_json=excluded.preferred_locations_json,updated_at=excluded.updated_at,
          allow_unknown_graduation=excluded.allow_unknown_graduation''',
          (uid,json.dumps(profile.skills),profile.interests,profile.graduation_year,
           int(profile.remote_only),json.dumps(profile.preferred_locations),now(),int(profile.allow_unknown_graduation)))

def get_user(uid,path=None):
    with connect(path) as con:
        row=con.execute('SELECT id,display_name,is_admin FROM users WHERE id=?',(uid,)).fetchone()
    return dict(row) if row else None

def get_resume(uid,path=None,include_data=False):
    columns='resume_name,resume_mime,resume_uploaded_at,resume_skills_json'
    if include_data:
        columns+=',resume_data'
    with connect(path) as con:
        row=con.execute(f'SELECT {columns} FROM profiles WHERE user_id=?',(uid,)).fetchone()
    if row is None or row['resume_name'] is None:
        return None
    result=dict(row)
    result['skills']=json.loads(result.pop('resume_skills_json') or '[]')
    return result

def replace_resume(uid,name,mime,data,extracted,path=None):
    """Replace the file and extracted profile together; never merge old skills."""
    from schemas import ResumeExtraction
    extracted=ResumeExtraction.model_validate(extracted.model_dump())
    if not extracted.is_resume:
        raise ValueError('The uploaded document does not appear to be a resume.')
    with connect(path) as con:
        current=con.execute('SELECT graduation_year FROM profiles WHERE user_id=?',(uid,)).fetchone()
        if current is None:
            raise ValueError('Profile not found')
        profile=Profile(skills=extracted.skills,interests=extracted.interests,
            graduation_year=extracted.graduation_year or current['graduation_year'])
        stamp=now()
        con.execute('''UPDATE profiles SET skills_json=?,interests=?,graduation_year=?,updated_at=?,
            resume_name=?,resume_mime=?,resume_data=?,resume_uploaded_at=?,resume_skills_json=? WHERE user_id=?''',
            (json.dumps(profile.skills),profile.interests,profile.graduation_year,stamp,
             name,mime,data,stamp,json.dumps(profile.skills),uid))
    return get_profile(uid,path)

def get_profile(uid, path=None):
    with connect(path) as con:
        row = con.execute('SELECT * FROM profiles WHERE user_id=?', (uid,)).fetchone()
    if row is None:
        raise ValueError('Profile not found')
    return Profile(skills=json.loads(row['skills_json']), interests=row['interests'],
        graduation_year=row['graduation_year'],remote_only=bool(row['remote_only']),
        preferred_locations=json.loads(row['preferred_locations_json']),
        allow_unknown_graduation=bool(row['allow_unknown_graduation']))

def update_preferences(uid, args: PreferenceArgs, path=None):
    # Read and update in one transaction, preserving unrelated fields.
    with connect(path) as con:
        if args.add_skills or args.remove_skills:
            query='SELECT skills_json FROM profiles WHERE user_id=?'
            if cloud_storage.enabled(path):
                query+=' FOR UPDATE'
            row=con.execute(query,(uid,)).fetchone()
            if row is None:
                raise ValueError('Profile not found')
            skills=preference_skills(json.loads(row['skills_json']),args)
            con.execute('UPDATE profiles SET skills_json=?,updated_at=? WHERE user_id=?',
                (json.dumps(skills),now(),uid))
        if args.remote_only is not None:
            con.execute('UPDATE profiles SET remote_only=?,updated_at=? WHERE user_id=?',
                        (int(args.remote_only),now(),uid))
        if args.preferred_locations is not None:
            con.execute('UPDATE profiles SET preferred_locations_json=?,updated_at=? WHERE user_id=?',
                        (json.dumps(args.preferred_locations),now(),uid))
    return get_profile(uid,path)

def set_feedback(uid, job_id, action, path=None):
    if action not in ('saved','hidden',None):
        raise ValueError('Unsupported feedback action')
    with connect(path) as con:
        if action is None:
            con.execute('DELETE FROM feedback WHERE user_id=? AND job_id=?',(uid,job_id))
        else:
            con.execute('''INSERT INTO feedback VALUES (?,?,?,?) ON CONFLICT(user_id,job_id)
              DO UPDATE SET action=excluded.action,created_at=excluded.created_at''',
              (uid,job_id,action,now()))

def get_feedback(uid,path=None):
    with connect(path) as con:
        return {r['job_id']:r['action'] for r in con.execute('SELECT * FROM feedback WHERE user_id=?',(uid,))}

def get_jobs(path=None):
    with connect(path) as con:
        rows = con.execute('SELECT * FROM jobs ORDER BY id').fetchall()
    jobs=[]
    for row in rows:
        job=dict(row)
        for key in ('required_skills','eligible_graduation_years','compatible_locations'):
            job[key]=json.loads(job.pop(key+'_json') or 'null')
        job['is_active']=bool(job['is_active'])
        jobs.append(job)
    return jobs
