"""Exercise authenticated navigation, persisted feedback, and configuration errors."""
from streamlit.testing.v1 import AppTest
from pathlib import Path
import pytest
import db
from app_runtime import refresh_project_modules

# Initialize source tracking before installing test doubles, just as a fresh server does.
refresh_project_modules()

APP=Path(__file__).resolve().parents[1]/'app.py'

def test_public_admin_hint_and_login(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception
    assert any('DUMMY' in c.value and 'ADMIN' in c.value for c in at.caption)
    at.text_input[0].set_value('ADMIN')
    at.button[0].click().run()
    assert not at.exception
    assert any(t.value=='Admin dashboard' for t in at.title)
    assert any(b.label=='Save internship' for b in at.button)

def test_invited_student_journey(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    db.init_db()
    from import_jobs import import_jobs
    import_jobs('data/jobs.csv')
    code=db.create_user('Abhinav')
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    assert not at.exception
    assert any('Hi, Abhinav' in item.value for item in at.sidebar.markdown)
    at.radio[0].set_value('Profile').run()
    at.text_input[0].set_value('python, sql')
    next(b for b in at.button if b.label=='Save profile').click().run()
    assert not at.exception
    at.radio[0].set_value('Matches').run()
    at.selectbox[0].set_value('keyword')
    next(b for b in at.button if b.label=='Find matches').click().run()
    assert not at.exception
    next(b for b in at.button if b.label=='Save').click().run()
    assert not at.exception
    uid=db.authenticate(code)['id']
    assert 'saved' in db.get_feedback(uid).values()
    next(b for b in at.button if b.label=='Hide').click().run()
    assert not at.exception
    assert 'hidden' in db.get_feedback(uid).values()
    at.radio[0].set_value('Saved').run()
    next(b for b in at.button if b.label=='Restore').click().run()
    assert 'hidden' not in db.get_feedback(uid).values()
    assert not at.exception
    next(b for b in at.button if b.label=='Sign out').click().run()
    at.text_input[0].set_value(code)
    next(b for b in at.button if b.label=='Sign in').click().run()
    assert db.get_profile(uid).skills==['python','sql']
    assert not at.exception
    assert at.radio[0].value=='Matches'

@pytest.mark.parametrize('last_page',['Profile','Saved','Chat'])
@pytest.mark.parametrize('switch_account',[False,True])
def test_every_student_login_starts_on_matches(tmp_path,monkeypatch,last_page,switch_account):
    import configuration
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    monkeypatch.setattr(configuration,'chat_config',lambda: (None,None,'Chat not configured for this test.'))
    db.init_db()
    first=db.create_user('Abhinav')
    second=db.create_user('Geetesh') if switch_account else first
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(first)
    at.button[0].click().run()
    at.radio[0].set_value(last_page).run()
    assert at.radio[0].value==last_page
    next(b for b in at.button if b.label=='Sign out').click().run()
    at.text_input[0].set_value(second)
    next(b for b in at.button if b.label=='Sign in').click().run()
    assert not at.exception
    assert at.radio[0].value=='Matches'
    assert any(title.value=='Find internships' for title in at.title)

def test_chat_configuration_error_does_not_break_navigation(tmp_path,monkeypatch):
    import configuration
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    monkeypatch.setattr(configuration,'chat_config',lambda: (None,None,'Check secrets.toml: key needs quotes.'))
    db.init_db()
    code=db.create_user('Abhinav')
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    at.radio[0].set_value('Chat').run()
    assert not at.exception
    assert 'quotes' in at.warning[0].value
    assert at.chat_input[0].disabled
    at.radio[0].set_value('Profile').run()
    assert not at.exception
    assert at.text_input[0].label=='Skills'

def test_chat_preference_confirmation_ui(tmp_path,monkeypatch):
    import configuration,agent
    from test_agent import FakeClient,response
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    monkeypatch.setattr(configuration,'chat_config',lambda: ('fake','test',None))
    client=FakeClient([response([('update_preferences',{'remote_only':True,'preferred_locations':['india']})]),
        response(text='Preferences saved.')])
    original=agent.Agent
    monkeypatch.setattr(agent,'Agent',lambda *args,**kwargs: original(*args,**kwargs,client=client))
    db.init_db()
    code=db.create_user('Geetesh')
    uid=db.authenticate(code)['id']
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    at.radio[0].set_value('Chat').run()
    at.chat_input[0].set_value('Only remote roles in India').run()
    assert not at.exception
    assert not db.get_profile(uid).remote_only
    next(b for b in at.button if b.label=='Confirm change').click().run()
    assert not at.exception
    assert db.get_profile(uid).remote_only
    assert db.get_profile(uid).preferred_locations==['india']

def test_chat_skill_confirmation_preview(tmp_path,monkeypatch):
    import configuration,agent
    from test_agent import FakeClient,response
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    monkeypatch.setattr(configuration,'chat_config',lambda: ('fake','test',None))
    client=FakeClient([response([('update_preferences',{'add_skills':['Docker'],'remove_skills':['Java']})]),
        response(text='Skills saved.')])
    original=agent.Agent
    monkeypatch.setattr(agent,'Agent',lambda *args,**kwargs: original(*args,**kwargs,client=client))
    db.init_db()
    code=db.create_user('Student')
    uid=db.authenticate(code)['id']
    from schemas import Profile
    db.save_profile(uid,Profile(skills=['Java','Python']))
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    at.radio[0].set_value('Chat').run()
    at.chat_input[0].set_value('I know Docker; remove Java').run()
    assert not at.exception
    assert any('Add skills: docker' in m.value for m in at.markdown)
    assert any('Remove skills: java' in m.value for m in at.markdown)
    assert any('Skills after confirmation: docker, python' in m.value for m in at.markdown)
    assert db.get_profile(uid).skills==['java','python']
    next(b for b in at.button if b.label=='Confirm change').click().run()
    assert not at.exception
    assert db.get_profile(uid).skills==['docker','python']


def test_resume_upload_resets_manual_skills_in_ui(tmp_path,monkeypatch):
    import streamlit as st
    import resume_profile
    from test_resume import ExtractClient
    from types import SimpleNamespace
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    db.init_db()
    code=db.create_user('Rohan')
    uid=db.authenticate(code)['id']
    current={'name':'first.txt','skills':['python','sql']}
    monkeypatch.setattr(st,'file_uploader',lambda *a,**kw: SimpleNamespace(
        name=current['name'],getvalue=lambda: b'Fictional student resume with software projects and skills.'))
    original=resume_profile.upload_resume
    monkeypatch.setattr(resume_profile,'upload_resume',lambda *a,**kw: original(
        *a,**kw,client=ExtractClient(current['skills'])))
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    at.radio[0].set_value('Profile').run()
    next(b for b in at.button if b.label=='Create profile from resume').click().run()
    assert not at.exception
    assert at.text_input[0].value=='python, sql'
    at.text_input[0].set_value('python, sql, docker')
    next(b for b in at.button if b.label=='Save profile').click().run()
    assert 'docker' in db.get_profile(uid).skills
    current.update(name='latest.txt',skills=['javascript','react'])
    next(b for b in at.button if b.label=='Create profile from resume').click().run()
    assert not at.exception
    assert db.get_profile(uid).skills==['javascript','react']
    assert at.text_input[0].value=='javascript, react'
    assert db.get_resume(uid)['resume_name']=='latest.txt'

def test_login_recovers_cached_db_module(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    db.init_db()
    code=db.create_user('Rishi')
    at=AppTest.from_file(APP,default_timeout=30).run()
    monkeypatch.delattr(db,'get_user')
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    assert not at.exception
    assert at.radio[0].value=='Matches'

def test_old_agent_module_recovers_for_profile_and_chat(tmp_path,monkeypatch):
    import agent,configuration
    from google import genai
    from test_agent import FakeClient,response
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    db.init_db()
    code=db.create_user('Amit')
    at=AppTest.from_file(APP,default_timeout=30).run()
    class OldAgent:
        def __init__(self,uid,api_key,search_fn):
            raise AssertionError('Outdated constructor should be refreshed')
    monkeypatch.setattr(agent,'Agent',OldAgent)
    monkeypatch.delattr(agent,'provider_error')
    monkeypatch.setattr(configuration,'chat_config',lambda: ('fake','test',None))
    monkeypatch.setattr(genai,'Client',lambda **kwargs: FakeClient([response(text='Ready to search.')]))
    at.text_input[0].set_value(code)
    at.button[0].click().run()
    at.radio[0].set_value('Profile').run()
    assert not at.exception
    assert any(b.label=='Create profile from resume' for b in at.button)
    at.radio[0].set_value('Chat').run()
    assert not at.exception and not at.error
    assert not at.chat_input[0].disabled
    at.chat_input[0].set_value('Hello').run()
    assert not at.exception
    assert any('Ready to search.' in m.value for m in at.markdown)

def test_admin_dashboard_adds_listing_and_student_has_no_access(tmp_path,monkeypatch):
    import catalog_admin,admin_dashboard,embeddings
    from test_admin import seed_csv
    from datetime import date
    import numpy as np
    monkeypatch.setattr(db,'STATE_DIR',tmp_path)
    monkeypatch.setattr(embeddings,'STATE_DIR',tmp_path)
    target=tmp_path/'jobs.csv'
    seed_csv(target)
    monkeypatch.setattr(catalog_admin,'CSV_PATH',target)
    monkeypatch.setattr(admin_dashboard,'CSV_PATH',target)
    class Encoder:
        def encode(self,texts,**kwargs):return np.ones((len(texts),4),dtype=np.float32)/2
    monkeypatch.setattr(embeddings,'load_model',lambda:Encoder())
    password=catalog_admin.create_admin()
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.text_input[0].set_value(password)
    at.button[0].click().run()
    assert not at.exception
    assert any(h.value=='Admin dashboard' for h in at.title)
    for label,value in [('Job title','UI-added Python Intern'),('Company','Test Company'),
        ('Original listing URL','https://example.org/ui-intern'),('Required skills','python, sql'),
        ('Display location','India'),('Compatible cities / countries','India'),('Eligible graduation years','2028')]:
        next(x for x in at.text_input if x.label==label).set_value(value)
    at.text_area[0].set_value('Build Python services and SQL database queries for this test internship.')
    at.selectbox[0].set_value('remote')
    next(b for b in at.button if b.label=='Save internship').click().run()
    assert not at.exception
    from import_jobs import read_jobs
    assert len(read_jobs(target))==2
    assert any(j['title']=='UI-added Python Intern' for j in db.get_jobs())
    next(b for b in at.button if b.label=='Sign out').click().run()
    student=db.create_user('Student')
    at.text_input[0].set_value(student)
    at.button[0].click().run()
    assert not at.exception
    assert at.radio[0].options==['Matches','Profile','Saved','Chat']
    assert not any(b.label=='Save internship' for b in at.button)
