"""Materialise the manually curated local ledger and fixed pre-ranking labels."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def prepare():
    existing=ROOT/'data/jobs.csv'
    if existing.exists():
        from import_jobs import read_jobs
        if len(read_jobs(existing))>52:
            raise SystemExit('Catalog contains web/admin additions. Keeping jobs.csv unchanged; use the admin dashboard to add listings.')
    ledger=json.loads((ROOT/'data/curated_records.json').read_text(encoding='utf-8'))
    rows=[]
    for company,title,url,description,skills,mode,location,years in ledger:
        compatible=None
        if location:
            compatible=[s.strip().lower() for s in location.split(';')]
            for country in ('United States','United Kingdom','Canada','India','Singapore','Spain','Germany','Thailand','Sweden'):
                if country.casefold() in location.casefold():
                    compatible.append(country.casefold())
            # Named office cities are compatible with the matching city preference only.
            compatible += [s.strip().split(',')[0].lower() for s in location.split(';')]
            compatible=sorted(set(compatible))
        # Conflicting or unverified remote geography must remain unknown.
        if company in ('Gensyn','Cohere'):
            compatible=None
        rows.append(dict(source_url=url,title=title,company=company,description=description,
            required_skills=json.dumps(skills),work_mode=mode or '',location=location or '',
            eligible_graduation_years=json.dumps(years),last_checked_at='2026-10-24',
            is_active=str(company not in ('Amazon','Airwallex') and not (company=='1Password' and 'Fall' in title)).lower(),
            compatible_locations=json.dumps(compatible)))
    with (ROOT/'data/jobs.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    # Labels established from job descriptions, before rankings. URLs survive database reimports.
    group={
        'web':[r['source_url'] for r in rows if r['company'] in ('Vercel','Klaviyo','Glean','Monzo') and json.loads(r['eligible_graduation_years'])],
        'quant':[r['source_url'] for r in rows if r['company'] in ('Graviton Research Capital','Walleye Capital','DV Trading')],
        'analytics':[r['source_url'] for r in rows if r['company'] in ('Anduril Industries','Leland') and json.loads(r['eligible_graduation_years'])],
    }
    specs=[('dev-web',['javascript','react'],'Build accessible web interfaces','web'),
        ('dev-quant',['python','c++','algorithms'],'Quantitative trading systems','quant'),
        ('dev-data',['python','sql','excel'],'Financial analytics and dashboards','analytics'),
        ('dev-backend',['go','postgres'],'Banking backend and platform engineering','web'),
        ('dev-ml',['python','pytorch','unix'],'Machine learning for systematic trading','quant'),
        ('test-ui',['typescript','css'],'Frontend product development','web'),
        ('test-lowlatency',['c++','data structures'],'Low latency financial systems','quant'),
        ('test-finance',['sql','financial statements'],'Finance reporting and workflow automation','analytics'),
        ('test-platform',['python','django'],'Scalable customer software and platform engineering','web'),
        ('test-research',['python','machine learning','unix'],'Quantitative development and trading research','quant')]
    cases=[dict(id=name,split='dev' if name.startswith('dev') else 'test',
        profile=dict(skills=skills,interests=interests,graduation_year=2028,remote_only=False,preferred_locations=[]),
        relevant_urls=group[label],rationale=f'Relevant to {label} interests based on manually read role descriptions.')
        for name,skills,interests,label in specs]
    (ROOT/'data/evaluation_cases.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    print(f'Prepared {len(rows)} real source records and {len(cases)} labeled profiles.')

if __name__=='__main__':
    prepare()
