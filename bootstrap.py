"""Refresh older local DB modules retained across Streamlit script reruns."""
import importlib

def current_database(module):
    import schemas
    if not hasattr(schemas,'ResumeExtraction'):
        importlib.invalidate_caches()
        importlib.reload(schemas)
    if not all(hasattr(module,name) for name in ('get_user','get_resume','replace_resume')):
        state_dir=module.STATE_DIR
        importlib.invalidate_caches()
        module=importlib.reload(module)
        module.STATE_DIR=state_dir
    return module
