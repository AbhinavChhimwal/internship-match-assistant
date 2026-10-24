"""One retrieval pipeline shared by the form, chat, and evaluation."""
from collections import Counter
import re
import numpy as np
from schemas import normalize
from embeddings import load_embeddings, load_model

def exclusion(job,profile,hidden):
    if not job['is_active']:
        return 'inactive'
    if job['id'] in hidden:
        return 'hidden'
    if profile.remote_only and job['work_mode']!='remote':
        return 'missing work arrangement' if job['work_mode'] is None else 'not remote'
    years=job['eligible_graduation_years']
    if not years and not profile.allow_unknown_graduation:
        return 'missing graduation eligibility'
    if years and profile.graduation_year not in years:
        return 'graduation year not accepted'
    if profile.preferred_locations:
        locations=job.get('compatible_locations')
        if not locations:
            return 'missing location compatibility'
        if not set(map(normalize,locations)) & set(profile.preferred_locations):
            return 'location not compatible'
    # Remote with unspecified geographic scope is never assumed worldwide.
    if profile.remote_only and not job.get('compatible_locations'):
        return 'missing remote geography'
    if profile.remote_only and not profile.preferred_locations:
        return 'remote search needs a location preference'
    return None

def profile_text(profile,query=''):
    return f'Student seeking internships. Skills: {", ".join(profile.skills)}. Interests: {profile.interests}. Search: {query}'

def search_jobs(jobs,profile,hidden=(),query='',method='combined',directory=None,encoder=None,vectors=None):
    if method not in ('keyword','semantic','combined'):
        raise ValueError('Unknown ranking method')
    reasons=Counter()
    eligible=[]
    for job in jobs:
        reason=exclusion(job,profile,set(hidden))
        if reason:
            reasons[reason]+=1
        else:
            eligible.append(job)
    if not eligible:
        return {'results':[],'omitted':dict(reasons),'eligible_count':0,'method':method}
    if method!='keyword':
        vectors=vectors if vectors is not None else load_embeddings(jobs,directory)
        model=encoder or load_model()
        q=np.asarray(model.encode([profile_text(profile,query)],normalize_embeddings=True))[0]
    keywords=set(profile.skills) | {normalize(t) for t in re.findall(r'[\w+#.]+',query.casefold())}
    results=[]
    for job in eligible:
        required=set(map(normalize,job['required_skills'] or []))
        matched=sorted(required & set(profile.skills))
        missing=sorted(required-set(profile.skills))
        coverage=len(matched)/len(required) if required else None
        if method=='keyword':
            score=len(required & keywords)/len(required) if required else 0.0
            similarity=None
        else:
            v=np.asarray(vectors[job['id']])
            similarity=float(np.dot(q,v)/(max(float(np.linalg.norm(q)*np.linalg.norm(v)),1e-12)))
            score=similarity if method=='semantic' or coverage is None else .8*similarity+.2*coverage
        results.append({**job,'score':score,'semantic_similarity':similarity,
            'skill_coverage':coverage,'matching_skills':matched,'missing_skills':missing})
    results.sort(key=lambda j:(-j['score'],j['id']))
    return {'results':results[:5],'omitted':dict(reasons),'eligible_count':len(eligible),'method':method}
