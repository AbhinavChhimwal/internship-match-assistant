from configuration import chat_config
from agent import provider_error
from types import SimpleNamespace

def test_invalid_secret_is_actionable_and_private(tmp_path,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    path=tmp_path/'secrets.toml'
    path.write_text('GEMINI_API_KEY = private-token-no-quotes')
    key,model,error=chat_config(path)
    assert key is None and 'quotes' in error
    assert 'private-token' not in error

def test_reload_secret_and_model_override(tmp_path,monkeypatch):
    for name in ('GEMINI_API_KEY','GEMINI_MODEL'):
        monkeypatch.delenv(name,raising=False)
    path=tmp_path/'secrets.toml'
    path.write_text('GEMINI_API_KEY = " first "\nGEMINI_MODEL = "test-model"')
    assert chat_config(path)==('first','test-model',None)
    path.write_text('GEMINI_API_KEY = "second"')
    assert chat_config(path)[0]=='second'

def test_provider_errors_do_not_expose_details():
    for code,expected in ((429,'quota'),(403,'permissions'),(404,'model'),(503,'temporarily')):
        message=provider_error(SimpleNamespace(code=code,message='PRIVATE KEY'))
        assert expected in message
        assert 'PRIVATE' not in message
