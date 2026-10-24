import numpy as np
import pytest
from schemas import Profile
from search import search_jobs

def test_remote_location_year_inactive_and_hidden(job):
    profile=Profile(skills=['python'],remote_only=True,preferred_locations=['india'])
    jobs=[job,{**job,'id':2,'work_mode':'hybrid'},
        {**job,'id':3,'eligible_graduation_years':None},
        {**job,'id':4,'is_active':False},{**job,'id':5},
        {**job,'id':6,'compatible_locations':['canada']},
        {**job,'id':7,'compatible_locations':None},
        {**job,'id':8,'eligible_graduation_years':[2027]}]
    for method in ('keyword','semantic','combined'):
        class Encoder:
            def encode(self,*args,**kwargs): return np.array([[1.,0.]])
        result=search_jobs(jobs,profile,hidden=[5],method=method,
            encoder=Encoder(),vectors={j['id']:np.array([1.,0.]) for j in jobs})
        assert [j['id'] for j in result['results']]==[1]
        assert sum(result['omitted'].values())==7

def test_empty_never_relaxes(job):
    result=search_jobs([job],Profile(graduation_year=2035),method='keyword')
    assert result['results']==[]

def test_remote_needs_explicit_country(job):
    result=search_jobs([job],Profile(remote_only=True),method='keyword')
    assert not result['results']

def test_fewer_than_five_and_aliases(job):
    result=search_jobs([{**job,'required_skills':['javascript','postgresql']}],
        Profile(skills=['js','postgres']),method='keyword')
    assert len(result['results'])==1
    assert result['results'][0]['skill_coverage']==1

def test_combined_ranking_and_unknown_skills(job):
    class Encoder:
        def encode(self,*args,**kwargs): return np.array([[1.,0.]])
    result=search_jobs([job,{**job,'id':2,'required_skills':None}],Profile(skills=['python']),
        encoder=Encoder(),vectors={1:np.array([.6,.8]),2:np.array([.6,.8])})
    scores={j['id']:j for j in result['results']}
    assert scores[1]['score']==pytest.approx(.8*.6+.2*.5)
    assert scores[2]['score']==pytest.approx(.6)
    assert scores[2]['skill_coverage'] is None
