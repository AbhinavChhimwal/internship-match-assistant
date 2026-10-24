import db
import pytest
from pydantic import ValidationError
from schemas import Profile, PreferenceArgs

def test_none_unchanged_empty_clears_and_restart(database):
    path,uid,_=database
    original=Profile(skills=['Python'],interests='APIs',graduation_year=2027,
        remote_only=True,preferred_locations=['India'])
    db.save_profile(uid,original,path)
    db.update_preferences(uid,PreferenceArgs(remote_only=False),path)
    profile=db.get_profile(uid,path)
    assert profile.preferred_locations==['india']
    assert not profile.remote_only
    db.update_preferences(uid,PreferenceArgs(preferred_locations=[]),path)
    profile=db.get_profile(uid,path)  # A new connection, no browser/session state.
    assert profile.preferred_locations==[]
    assert profile.skills==['python'] and profile.graduation_year==2027 and profile.interests=='APIs'

def test_user_isolation_and_token_hash(database):
    path,uid,code=database
    other_code=db.create_user('Other',path)
    other=db.authenticate(other_code,path)['id']
    db.update_preferences(other,PreferenceArgs(remote_only=True),path)
    assert not db.get_profile(uid,path).remote_only
    assert db.authenticate('incorrect',path) is None
    with db.connect(path) as con:
        assert con.execute('SELECT access_token_hash FROM users WHERE id=?',(uid,)).fetchone()[0]!=code

def test_reject_user_id_and_coercion():
    for raw in ({'user_id':99},{'remote_only':'false'},{'skills':['python']}):
        with pytest.raises(ValidationError):
            PreferenceArgs.model_validate(raw)

def test_feedback_upsert_and_persistence(database):
    from import_jobs import import_jobs
    path,uid,_=database
    import_jobs('data/jobs.csv',path)
    job_id=db.get_jobs(path)[0]['id']
    db.set_feedback(uid,job_id,'saved',path)
    db.set_feedback(uid,job_id,'hidden',path)
    assert db.get_feedback(uid,path)=={job_id:'hidden'}
    with db.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]==1
