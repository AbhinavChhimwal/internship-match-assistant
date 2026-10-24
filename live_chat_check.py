"""Optional real-provider acceptance test, isolated from student accounts."""
import json
import uuid
from pathlib import Path
import db
from configuration import chat_config
from agent import Agent
from import_jobs import import_jobs
from schemas import Profile
from search import search_jobs

def main():
    key,model,error=chat_config()
    if error:
        raise SystemExit(error)
    path=Path('runtime')/('live-chat-check-'+uuid.uuid4().hex+'.db')
    db.init_db(path)
    code=db.create_user('Synthetic Chat Check',path)
    uid=db.authenticate(code,path)['id']
    db.save_profile(uid,Profile(skills=['python','sql'],interests='backend development'),path)
    import_jobs('data/jobs.csv',path)
    searches=[]
    def search(query):
        searches.append(query)
        return search_jobs(db.get_jobs(path),db.get_profile(uid,path),query=query)
    agent=Agent(uid,key,search,path=path,model=model)
    checks=[]
    cases=[('Find Python backend internships.','search'),('Only remote roles.','remote'),
        ('Bengaluru is okay now.','location'),('Forget my location preference.','clear'),
        ('Show my saved jobs.','unsupported')]
    for message,kind in cases:
        before=db.get_profile(uid,path)
        count=len(searches)
        outcome=agent.start(message)
        pending=outcome.get('pending')
        unchanged=db.get_profile(uid,path)==before
        if pending:
            outcome=agent.resume(pending,True)
        after=db.get_profile(uid,path)
        expected={'search':len(searches)>count,'remote':after.remote_only,
            'location':after.preferred_locations==['bengaluru'],
            'clear':after.preferred_locations==[],
            'unsupported':'saved' in outcome['text'].lower() and not pending and len(searches)==count}[kind]
        passed=expected and unchanged and not outcome.get('error')
        if kind in ('remote','location','clear'):
            passed=passed and bool(pending)
        row={'case':kind,'passed':bool(passed),'provider_error':outcome.get('error',False),
            'confirmation_requested':bool(pending),'unchanged_before_confirm':unchanged,
            'search_executed':len(searches)>count}
        print(json.dumps(row),flush=True)
        checks.append(row)
    output={'model':model,'checks':checks,'all_passed':all(c['passed'] for c in checks)}
    Path('runtime/live_chat_validation.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    return 0 if output['all_passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
