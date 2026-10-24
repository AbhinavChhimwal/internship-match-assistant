import io
import json
from types import SimpleNamespace as NS
import zipfile
import pytest
import db
from bootstrap import current_database
from resume_profile import prepare_resume,upload_resume
from schemas import ResumeExtraction,Profile
from search import search_jobs

class ExtractClient:
    def __init__(self,skills,year=2028):
        self.models=self
        self.skills=skills
        self.year=year
        self.requests=[]
    def generate_content(self,**kwargs):
        self.requests.append(kwargs)
        return NS(parsed=ResumeExtraction(is_resume=True,skills=self.skills,
            interests='Project development',graduation_year=self.year))

def test_new_resume_replaces_manual_skills_and_previous_file(database):
    path,uid,_=database
    first=b'Student resume. Skills: Python and SQL. Graduation 2028.'
    upload_resume(uid,'first.txt',first,path,client=ExtractClient(['Python','SQL']))
    profile=db.get_profile(uid,path)
    profile.skills.append('docker')
    profile.remote_only=True
    profile.allow_unknown_graduation=True
    profile.preferred_locations=['india']
    db.save_profile(uid,profile,path)
    assert 'docker' in db.get_profile(uid,path).skills
    latest=b'Updated student resume. Skills: JavaScript. Graduation 2028.'
    upload_resume(uid,'latest.txt',latest,path,client=ExtractClient(['JS']))
    assert db.get_profile(uid,path).skills==['javascript']
    assert db.get_profile(uid,path).remote_only
    assert db.get_profile(uid,path).allow_unknown_graduation
    assert db.get_profile(uid,path).preferred_locations==['india']
    saved=db.get_resume(uid,path,include_data=True)
    assert saved['resume_name']=='latest.txt' and saved['resume_data']==latest
    assert saved['skills']==['javascript']
    assert 'resume_data' not in db.get_resume(uid,path)

def test_schema_sent_to_gemini_is_supported(database):
    path,uid,_=database
    client=ExtractClient(['python'])
    upload_resume(uid,'cv.txt',b'Student resume with Python projects and skills.',path,client=client)
    schema=client.requests[0]['config'].response_schema
    assert isinstance(schema,dict)
    assert 'additionalProperties' not in schema
    assert set(schema['properties'])=={'is_resume','skills','interests','graduation_year'}

def test_failed_extract_keeps_resume_and_profile(database):
    path,uid,_=database
    data=b'Resume with experience in Python and SQL for backend development.'
    upload_resume(uid,'resume.txt',data,path,client=ExtractClient(['python']))
    before=db.get_profile(uid,path)
    class FailedClient:
        def __init__(self): self.models=self
        def generate_content(self,**kwargs): raise RuntimeError('private details')
    with pytest.raises(ValueError,match='previous resume and profile were kept') as error:
        upload_resume(uid,'new.txt',data,path,client=FailedClient())
    assert 'private' not in str(error.value)
    assert db.get_profile(uid,path)==before
    assert db.get_resume(uid,path,include_data=True)['resume_data']==data

def test_resume_account_isolation_and_unknown_year(database):
    path,uid,_=database
    other=db.authenticate(db.create_user('Other',path),path)['id']
    db.save_profile(uid,Profile(graduation_year=2027,interests='Old interests'),path)
    upload_resume(uid,'resume.txt',b'Resume skills in Python and statistics without dates.',path,
        client=ExtractClient(['python'],year=None))
    assert db.get_resume(other,path,include_data=True) is None
    assert db.get_profile(other,path).skills==[]
    assert db.get_profile(uid,path).graduation_year==2027
    assert db.get_profile(uid,path).interests=='Project development'

def test_resume_skills_drive_search(database,job):
    path,uid,_=database
    jobs=[{**job,'id':1,'required_skills':['python']},{**job,'id':2,'required_skills':['javascript']}]
    data=b'Student resume with software engineering projects and listed skills.'
    upload_resume(uid,'python.txt',data,path,client=ExtractClient(['python']))
    assert search_jobs(jobs,db.get_profile(uid,path),method='keyword')['results'][0]['id']==1
    upload_resume(uid,'javascript.txt',data,path,client=ExtractClient(['javascript']))
    assert search_jobs(jobs,db.get_profile(uid,path),method='keyword')['results'][0]['id']==2

def test_file_types_and_bounds():
    with pytest.raises(ValueError): prepare_resume('virus.exe',b'anything')
    with pytest.raises(ValueError): prepare_resume('fake.pdf',b'not a pdf')
    with pytest.raises(ValueError): prepare_resume('huge.txt',b'a'*(5*1024*1024+1))
    with pytest.raises(ValueError): prepare_resume('empty.txt',b'')
    name,mime,part=prepare_resume('../cv.pdf',b'%PDF-1.4\nfixture only')
    assert name=='cv.pdf' and mime=='application/pdf'
    assert part.inline_data.data.startswith(b'%PDF')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Resume: Python and SQL project development skills.</w:t></w:r></w:p></w:body></w:document>''')
    _,_,part=prepare_resume('resume.docx',archive.getvalue())
    assert 'Python and SQL' in part.text

def test_invalid_model_result_not_saved(database):
    path,uid,_=database
    class BadClient:
        def __init__(self): self.models=self
        def generate_content(self,**kwargs): return NS(parsed=None,text=json.dumps({'skills':'SECRET'}))
    with pytest.raises(ValueError) as error:
        upload_resume(uid,'cv.txt',b'Student resume with listed skills Python and SQL.',path,client=BadClient())
    assert 'SECRET' not in str(error.value)
    assert db.get_resume(uid,path) is None

def test_stale_database_module_recovers(database,monkeypatch):
    state_dir=db.STATE_DIR
    monkeypatch.delattr(db,'get_user')
    current=current_database(db)
    assert callable(current.get_user) and callable(current.replace_resume)
    assert current.STATE_DIR==state_dir

def test_legacy_seven_column_profile_migrates(tmp_path):
    path=tmp_path/'old.db'
    with db.connect(path) as con:
        con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,display_name TEXT,access_token_hash TEXT);
            CREATE TABLE profiles(user_id INTEGER PRIMARY KEY,skills_json TEXT,interests TEXT,
            graduation_year INTEGER,remote_only INTEGER,preferred_locations_json TEXT,updated_at TEXT);
            INSERT INTO users VALUES(1,'Legacy','hash');
            INSERT INTO profiles VALUES(1,'["python"]','APIs',2027,0,'[]','old');''')
    db.init_db(path)
    assert db.get_profile(1,path).skills==['python']
    assert db.get_resume(1,path) is None
    profile=db.get_profile(1,path)
    profile.skills.append('sql')
    db.save_profile(1,profile,path)
    assert db.get_profile(1,path).skills==['python','sql']

def test_resume_import_does_not_depend_on_agent_error_helper(monkeypatch):
    import importlib,agent,resume_profile
    monkeypatch.delattr(agent,'provider_error')
    importlib.reload(resume_profile)
    assert callable(resume_profile.upload_resume)
