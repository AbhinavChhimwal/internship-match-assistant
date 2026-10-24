"""Keep local modules consistent when Streamlit reruns an updated app script."""
import hashlib
import importlib
import inspect
from pathlib import Path
import sys
import threading

_lock=threading.RLock()
MODULES=('settings','schemas','cloud_storage','supabase_wake','db','configuration','ai_errors','embeddings','search','agent','resume_profile',
         'import_jobs','cloud_startup','catalog_admin','admin_dashboard')

def refresh_project_modules():
    """Reload changed source and dependent modules, keeping the configured DB path.

    Streamlit reruns app.py, but Python's imported modules survive those reruns.
    Source fingerprints prevent mixing new UI code with old constructors/helpers.
    """
    root=Path(__file__).resolve().parent
    with _lock:
        upstream_changed=False
        for name in MODULES:
            digest=hashlib.sha256((root/f'{name}.py').read_bytes()).hexdigest()
            module=sys.modules.get(name)
            if module is None:
                module=importlib.import_module(name)
            else:
                missing_api=False
                if name=='db':
                    missing_api=not all(hasattr(module,n) for n in ('get_user','get_resume','replace_resume'))
                elif name=='agent':
                    parameters=inspect.signature(module.Agent).parameters
                    accepts_model='model' in parameters or any(p.kind==p.VAR_KEYWORD for p in parameters.values())
                    missing_api=not accepts_model or not hasattr(module,'provider_error')
                if upstream_changed or missing_api or getattr(module,'_matcher_source_digest',None)!=digest:
                    previous_state=getattr(module,'STATE_DIR',None) if name=='db' else None
                    importlib.invalidate_caches()
                    module=importlib.reload(module)
                    if previous_state is not None:
                        module.STATE_DIR=previous_state
                    upstream_changed=True
            module._matcher_source_digest=digest
