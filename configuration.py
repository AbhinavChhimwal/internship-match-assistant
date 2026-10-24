"""Reload local secrets and report configuration problems without exposing values."""
import os
import tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def chat_config(secrets_path=None):
    path=Path(secrets_path) if secrets_path else ROOT/'.streamlit'/'secrets.toml'
    values={}
    try:
        if path.exists():
            values=tomllib.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,tomllib.TOMLDecodeError):
        return None,None,'Check .streamlit/secrets.toml: use GEMINI_API_KEY = "your-key" (with quotes).'
    key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY')
    model=os.environ.get('GEMINI_MODEL') or values.get('GEMINI_MODEL') or 'gemini-3.1-flash-lite'
    if not isinstance(model,str) or not model.strip():
        return None,None,'GEMINI_MODEL must be a quoted model name.'
    if key is None:
        return None,model.strip(),'Add GEMINI_API_KEY to .streamlit/secrets.toml to enable chat.'
    if not isinstance(key,str) or not key.strip() or key.strip().startswith(('paste-','your-')):
        return None,model.strip(),'Enter a valid Gemini API key in .streamlit/secrets.toml.'
    return key.strip(),model.strip(),None
