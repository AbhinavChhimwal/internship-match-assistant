"""Optional real-Gemini test using fictional resumes in an isolated database."""
import json
from pathlib import Path
import uuid
import db
from resume_profile import upload_resume
from import_jobs import import_jobs
from search import search_jobs

def synthetic_pdf():
    lines=['FICTIONAL STUDENT RESUME','Education: B.Tech Computer Science. Expected graduation: 2028.',
           'Skills: Python, SQL, PostgreSQL.','Project: Developed a Python backend API and SQL database.']
    commands=['BT /F1 12 Tf 50 740 Td']
    for index,line in enumerate(lines):
        if index: commands.append('0 -24 Td')
        commands.append('('+line+') Tj')
    commands.append('ET')
    stream='\n'.join(commands).encode('ascii')
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=b'%PDF-1.4\n'
    offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(data))
        data+=f'{index} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(data)
    data+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]: data+=f'{offset:010d} 00000 n \n'.encode()
    data+=f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()
    return data

def main():
    path=Path('runtime')/('resume-live-'+uuid.uuid4().hex+'.db')
    db.init_db(path)
    uid=db.authenticate(db.create_user('Synthetic Resume Check',path),path)['id']
    first=upload_resume(uid,'backend.pdf',synthetic_pdf(),path)
    assert {'python','sql'}.issubset(first.skills) and first.graduation_year==2028
    profile=db.get_profile(uid,path)
    profile.skills.append('docker')
    db.save_profile(uid,profile,path)
    latest=b'FICTIONAL STUDENT RESUME\nEducation: B.Tech Computer Science, expected graduation 2028.\nSkills: JavaScript, React, HTML, CSS.\nProject: Built responsive web interfaces using React.'
    second=upload_resume(uid,'frontend.txt',latest,path)
    profile=db.get_profile(uid,path)
    assert {'javascript','react'}.issubset(profile.skills)
    assert not {'python','sql','docker'} & set(profile.skills)
    assert db.get_resume(uid,path,include_data=True)['resume_data']==latest
    import_jobs('data/jobs.csv',path)
    result=search_jobs(db.get_jobs(path),profile)
    assert result['results']
    report={'pdf_extraction':True,'txt_extraction':True,'new_resume_resets_old_and_manual_skills':True,
        'latest_resume_persisted':True,'semantic_search_from_extracted_profile':True,
        'result_count':len(result['results'])}
    Path('runtime/live_resume_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    main()
