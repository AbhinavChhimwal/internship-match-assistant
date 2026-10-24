"""All durable state can be moved to one persistent host volume."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_DIR = Path(os.environ.get('MATCHER_STATE_DIR', ROOT / 'runtime'))
os.environ.setdefault('HF_HOME', str(STATE_DIR / 'model-cache'))
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.1-flash-lite')
