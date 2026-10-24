"""Reproducible three-way comparison; held-out labels are never used for ranking."""
import argparse
import json
import os
import platform
import statistics
import time
from pathlib import Path
from db import get_jobs
from embeddings import load_model, load_embeddings, fingerprint
from schemas import Profile
from search import search_jobs
from settings import MODEL_NAME, STATE_DIR

def constraint_violations(results,profile):
    # Independent assertions, not the retrieval engine's filter function.
    violations=[]
    for job in results:
        years=job['eligible_graduation_years']
        bad=(not job['is_active'] or
            (profile.graduation_year not in years if years else not profile.allow_unknown_graduation))
        if profile.remote_only:
            bad |= job['work_mode']!='remote' or not job.get('compatible_locations') or not profile.preferred_locations
        if profile.preferred_locations:
            bad |= not bool(set(profile.preferred_locations)&set(job.get('compatible_locations') or []))
        if bad:
            violations.append(job['id'])
    return violations

def evaluate(split='test',methods=('keyword','semantic','combined'),repeats=5):
    jobs=get_jobs()
    cases=json.loads(Path('data/evaluation_cases.json').read_text())
    selected=[c for c in cases if c['split']==split]
    semantic=any(m!='keyword' for m in methods)
    model=load_model() if semantic else None
    vectors=load_embeddings(jobs) if semantic else None
    if model:
        model.encode(['Warm up model'],normalize_embeddings=True)
    rows=[]
    for case in selected:
        profile=Profile.model_validate(case['profile'])
        relevant=set(case['relevant_urls'])
        for method in methods:
            latencies=[]
            for _ in range(repeats):
                started=time.perf_counter()
                result=search_jobs(jobs,profile,method=method,encoder=model,vectors=vectors)
                latencies.append((time.perf_counter()-started)*1000)
            found=result['results']
            valid=result['eligible_count']>=5
            rows.append({'case':case['id'],'method':method,'eligible_count':result['eligible_count'],
                'precision_at_5':sum(j['source_url'] in relevant for j in found)/5 if valid else None,
                'comparison_note':None if valid else 'Skipped P@5: fewer than five eligible jobs.',
                'constraint_violations':constraint_violations(found,profile),
                'median_latency_ms':round(statistics.median(latencies),3),
                'returned_urls':[j['source_url'] for j in found]})
    summary={}
    for method in methods:
        group=[r for r in rows if r['method']==method]
        scores=[r['precision_at_5'] for r in group if r['precision_at_5'] is not None]
        summary[method]={'mean_precision_at_5':statistics.mean(scores) if scores else None,
            'evaluated_profiles':len(scores),'constraint_violations':sum(len(r['constraint_violations']) for r in group),
            'median_latency_ms':statistics.median(r['median_latency_ms'] for r in group)}
    return {'split':split,'model':MODEL_NAME,'dataset_fingerprint':fingerprint(jobs),
        'hardware':{'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count()},
        'timing':'Model loading excluded; warmed query encoding and in-memory filters/ranking included; median of five runs.',
        'limitations':'Ten fictional profiles, author-provided relevance labels, small eligible subset. Not evidence of hiring success or general model superiority.',
        'summary':summary,'cases':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['dev','test'],default='test')
    parser.add_argument('--keyword-only',action='store_true')
    args=parser.parse_args()
    report=evaluate(args.split,('keyword',) if args.keyword_only else ('keyword','semantic','combined'))
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    output=STATE_DIR/f'evaluation_{args.split}.json'
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))
    print(f'Report: {output}')
