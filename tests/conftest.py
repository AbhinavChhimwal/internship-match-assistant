import pytest
import db

@pytest.fixture(autouse=True)
def isolate_cloud_credentials(monkeypatch):
    # Routine regression tests must never touch the owner's configured cloud DB.
    monkeypatch.setenv('DATABASE_URL','')
    monkeypatch.setenv('SUPABASE_MANAGEMENT_TOKEN','')

@pytest.fixture
def database(tmp_path):
    path=tmp_path/'test.db'
    db.init_db(path)
    code=db.create_user('Student',path)
    return path,db.authenticate(code,path)['id'],code

@pytest.fixture
def job():
    return dict(id=1,is_active=True,work_mode='remote',eligible_graduation_years=[2028],
        compatible_locations=['india','bengaluru'],required_skills=['python','sql'],
        embedding_text='Python backend SQL',source_url='https://example.org/job',
        title='Python backend intern',company='Fixture only',description='Synthetic test fixture')
