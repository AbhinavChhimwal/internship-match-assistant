import hashlib
import json
from functools import lru_cache
from pathlib import Path
import numpy as np
from settings import MODEL_NAME, STATE_DIR

@lru_cache(maxsize=1)
def load_model():
    from sentence_transformers import SentenceTransformer
    # Cached weights should not require a network check on every app restart.
    try:
        return SentenceTransformer(MODEL_NAME,local_files_only=True)
    except OSError:
        return SentenceTransformer(MODEL_NAME)

def fingerprint(jobs):
    payload=[(j['id'],j['embedding_text']) for j in sorted(jobs,key=lambda j:j['id'])]
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode()).hexdigest()

def build_embeddings(jobs,directory=None):
    directory=Path(directory or STATE_DIR)
    directory.mkdir(parents=True,exist_ok=True)
    vectors=load_model().encode([j['embedding_text'] for j in jobs],normalize_embeddings=True)
    np.save(directory/'job_embeddings.npy',vectors,allow_pickle=False)
    (directory/'job_ids.json').write_text(json.dumps([j['id'] for j in jobs]),encoding='utf-8')
    (directory/'embedding_manifest.json').write_text(json.dumps({
        'model':MODEL_NAME,'fingerprint':fingerprint(jobs)}),encoding='utf-8')

def load_embeddings(jobs,directory=None):
    directory=Path(directory or STATE_DIR)
    try:
        meta=json.loads((directory/'embedding_manifest.json').read_text())
        ids=json.loads((directory/'job_ids.json').read_text())
        vectors=np.load(directory/'job_embeddings.npy',allow_pickle=False)
    except (OSError,ValueError) as error:
        raise ValueError('Embedding index unavailable. Run python embeddings.py.') from error
    if meta!={'model':MODEL_NAME,'fingerprint':fingerprint(jobs)} or len(ids)!=len(set(ids)) or set(ids)!={j['id'] for j in jobs}:
        raise ValueError('Embedding index is stale. Run python embeddings.py after every import.')
    if vectors.ndim!=2 or vectors.shape[0]!=len(ids) or not np.isfinite(vectors).all():
        raise ValueError('Invalid embedding vectors; rebuild the index.')
    return dict(zip(ids,vectors))

if __name__=='__main__':
    from db import get_jobs
    build_embeddings(get_jobs())
    print('Created job_embeddings.npy, job_ids.json and embedding_manifest.json in the state directory.')
