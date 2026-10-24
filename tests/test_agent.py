from types import SimpleNamespace as NS
from google.genai import types
from agent import Agent
import db
import pytest
from schemas import Profile

def response(calls=(),text=None):
    return NS(function_calls=[NS(name=n,args=a) for n,a in calls],text=text,
        candidates=[NS(content=types.Content(role='model',parts=[types.Part.from_text(text='fixture')]))])

class FakeClient:
    def __init__(self,responses):
        self.responses=iter(responses)
        self.models=self
        self.count=0
    def generate_content(self,**kwargs):
        self.count+=1
        return next(self.responses)

def test_confirmation_then_search(database):
    path,uid,_=database
    seen=[]
    def search(query):
        seen.append(db.get_profile(uid,path).remote_only)
        return {'results':[],'omitted':{}}
    client=FakeClient([response([('update_preferences',{'remote_only':True})]),
        response([('search_jobs',{'query':'python'})]),response(text='No matches.')])
    agent=Agent(uid,'unused',search,path,client)
    outcome=agent.start('Only remote roles')
    assert 'pending' in outcome
    assert not db.get_profile(uid,path).remote_only
    agent.resume(outcome['pending'],True)
    assert db.get_profile(uid,path).remote_only
    assert seen==[True]

def test_cancel_and_reject_invalid_user(database):
    path,uid,_=database
    client=FakeClient([response([('update_preferences',{'remote_only':True})]),response(text='Cancelled')])
    agent=Agent(uid,'unused',lambda q:None,path,client)
    outcome=agent.start('Only remote')
    agent.resume(outcome['pending'],False)
    assert not db.get_profile(uid,path).remote_only
    agent.client=FakeClient([response([('update_preferences',{'user_id':99})])])
    assert 'could not be completed' in agent.start('attack')['text']

def test_tool_budget_and_provider_failure(database):
    path,uid,_=database
    search=lambda q:{'results':[],'omitted':{}}
    client=FakeClient([response([('search_jobs',{'query':'python'})])]*5)
    agent=Agent(uid,'unused',search,path,client)
    assert 'limit' in agent.start('Search')['text']
    assert client.count==3
    agent.client=FakeClient([])
    assert 'unavailable' in agent.start('Search')['text']

def test_transient_retry_charged_and_quota_not_retried(database):
    path,uid,_=database
    class Failure(Exception):
        def __init__(self,code): self.code=code
    class FlakyClient:
        def __init__(self,code): self.code=code; self.count=0; self.models=self
        def generate_content(self,**kwargs):
            self.count+=1
            if self.count==1: raise Failure(self.code)
            return response(text='Try Matches.')
    charges=[]
    client=FlakyClient(503)
    agent=Agent(uid,'unused',lambda q:None,path,client,charge=lambda: charges.append(1))
    assert not agent.start('hello').get('error')
    assert client.count==2 and len(charges)==2
    client=FlakyClient(429)
    agent.client=client
    assert agent.start('hello')['error']
    assert client.count==1


def test_confirmed_skill_deltas_preserve_other_fields_and_drive_search(database):
    path,uid,_=database
    db.save_profile(uid,Profile(skills=['Python','Java'],interests='APIs',
        graduation_year=2027,preferred_locations=['India']),path)
    other=db.authenticate(db.create_user('Other',path),path)['id']
    observed=[]
    def search(query):
        observed.append(db.get_profile(uid,path).skills)
        return {'results':[],'omitted':{}}
    client=FakeClient([response([('update_preferences',{'add_skills':['Docker','JS'],
        'remove_skills':['Java']})]),response([('search_jobs',{'query':'backend'})]),response(text='Updated.')])
    agent=Agent(uid,'unused',search,path,client)
    proposed=agent.start('I also know Docker and JS. Remove Java.')
    assert db.get_profile(uid,path).skills==['java','python']
    agent.resume(proposed['pending'],True)
    saved=db.get_profile(uid,path)
    assert saved.skills==['docker','javascript','python']
    assert saved.interests=='APIs' and saved.graduation_year==2027
    assert saved.preferred_locations==['india']
    assert observed==[saved.skills]
    assert db.get_profile(other,path).skills==[]


def test_cancelled_skill_update_leaves_profile_unchanged(database):
    path,uid,_=database
    db.save_profile(uid,Profile(skills=['Python']),path)
    agent=Agent(uid,'unused',lambda q:None,path,FakeClient([
        response([('update_preferences',{'add_skills':['Docker'],'remove_skills':['Python']})]),
        response(text='Cancelled.')]))
    proposed=agent.start('Replace Python with Docker')
    agent.resume(proposed['pending'],False)
    assert db.get_profile(uid,path).skills==['python']


@pytest.mark.parametrize('change',[
    {'add_skills':['JS'],'remove_skills':['javascript']},
    {'skills':['Docker']},
    {'add_skills':'Docker'},
    {'add_skills':['Docker'],'user_id':99},
])
def test_invalid_skill_proposals_do_not_mutate_profile(database,change):
    path,uid,_=database
    agent=Agent(uid,'unused',lambda q:None,path,FakeClient([response([('update_preferences',change)])]))
    outcome=agent.start('Change skills')
    assert 'pending' not in outcome
    assert db.get_profile(uid,path).skills==[]


def test_skill_limit_checked_before_confirmation(database):
    path,uid,_=database
    db.save_profile(uid,Profile(skills=[f'skill{i}' for i in range(40)]),path)
    agent=Agent(uid,'unused',lambda q:None,path,FakeClient([
        response([('update_preferences',{'add_skills':['Docker']})])]))
    outcome=agent.start('I also know Docker')
    assert 'pending' not in outcome
    assert len(db.get_profile(uid,path).skills)==40


def test_search_tool_does_not_add_requested_technology(database):
    path,uid,_=database
    agent=Agent(uid,'unused',lambda q:{'results':[],'omitted':{}},path,FakeClient([
        response([('search_jobs',{'query':'React internships'})]),response(text='Results.')]))
    agent.start('Find React internships')
    assert db.get_profile(uid,path).skills==[]
