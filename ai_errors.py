"""Safe error messages shared by chat and resume extraction."""
def provider_error(error):
    """Never render raw provider diagnostics, which may contain credentials."""
    code=getattr(error,'code',None) or getattr(error,'status_code',None)
    status=str(getattr(error,'status','')).upper()
    if code==429 or status=='RESOURCE_EXHAUSTED':
        return 'Gemini quota or rate limit reached. Check your Google AI Studio quota, then try again. You can still use Matches.'
    if code in (401,403) or status in ('UNAUTHENTICATED','PERMISSION_DENIED'):
        return 'Gemini rejected this API key or its permissions. Check the key and API access in Google AI Studio.'
    if code==400:
        return 'Gemini rejected the request. Check that your API key and GEMINI_MODEL setting are valid.'
    if code==404:
        return 'The configured Gemini model is unavailable. Set GEMINI_MODEL in .streamlit/secrets.toml to a model available to your API key.'
    if code in (500,502,503,504):
        return 'Gemini is temporarily unavailable. Try again shortly, or use Matches.'
    return 'Chat is unavailable: the connection to Gemini failed or its response could not be processed. Check your connection and try again. Matches remains available.'
