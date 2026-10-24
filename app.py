from datetime import date
import time
import streamlit as st
from pydantic import ValidationError
from app_runtime import refresh_project_modules
refresh_project_modules()
import db
from configuration import chat_config
from schemas import Profile, PreferenceArgs, preference_skills
from search import search_jobs, exclusion
from agent import Agent
from ai_errors import provider_error

st.set_page_config(page_title='Internship Match', page_icon='🎓', layout='wide')
import cloud_storage
try:
    if cloud_storage.enabled():
        from cloud_startup import initialize_cloud
        initialize_cloud(progress=lambda: st.spinner('Connecting to saved data…'))
    else:
        db.init_db()
except cloud_storage.StorageUnavailable as error:
    st.error(str(error))
    if st.button('Retry connection'):
        st.rerun()
    st.stop()
st.markdown('''<style>
.block-container {max-width:1100px;padding-top:2rem;padding-bottom:2rem;}
h1 {font-size:2.1rem!important;letter-spacing:-.7px;}
h3 {font-size:1.2rem!important;}
[data-testid="stSidebar"] {border-right:1px solid #dfe6e3;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
[data-testid="stHeader"] {background:transparent;}
</style>''',unsafe_allow_html=True)

if 'user' not in st.session_state:
    _,center,_=st.columns([1,2,1])
    with center:
        st.title('Internship Match')
        st.write('Sign in to find and save internships.')
        with st.form('login',border=True):
            code=st.text_input('Access code or admin password',type='password',
                placeholder='Try the demo: DUMMY',
                help='Use DUMMY for the shared demo account. Everyone using this code shares its profile and saved data.')
            if st.form_submit_button('Sign in',type='primary',use_container_width=True):
                if time.monotonic()<st.session_state.get('login_after',0):
                    st.error('Wait a moment before trying again.')
                else:
                    user=db.authenticate(code)
                    if user:
                        st.session_state.user=user
                        # Explicitly override any navigation value retained by the browser.
                        st.session_state.navigation_page='Matches'
                        st.rerun()
                    st.session_state.login_after=time.monotonic()+2
                    st.error('Invalid access code. Check the code assigned to you.')
    st.stop()

user=db.get_user(st.session_state.user['id'])
if user is None:
    st.session_state.clear()
    st.rerun()
st.session_state.user=user
uid=user['id']
if user.get('is_admin'):
    with st.sidebar:
        st.title('Internship Match')
        st.write(f"**Hi, {user['display_name']}**")
        st.caption('Administrator')
        if st.button('Sign out',use_container_width=True):
            st.session_state.clear()
            st.rerun()
    from admin_dashboard import render_admin
    render_admin(uid)
    st.stop()
profile=db.get_profile(uid)
jobs=db.get_jobs()
feedback=db.get_feedback(uid)

with st.sidebar:
    st.title('Internship Match')
    st.write(f"**Hi, {user['display_name']}**")
    page=st.radio('Navigation',['Matches','Profile','Saved','Chat'],
        key='navigation_page',label_visibility='collapsed')
    st.divider()
    st.caption(f'Graduation: {profile.graduation_year}')
    if profile.remote_only:
        st.caption('Remote only')
    if profile.preferred_locations:
        st.caption(', '.join(profile.preferred_locations).title())
    if profile.allow_unknown_graduation:
        st.caption('Unverified graduation eligibility included')
    if st.button('Sign out',use_container_width=True):
        keep={k:v for k,v in st.session_state.items() if k in ('api_calls','login_after')}
        st.session_state.clear()
        st.session_state.update(keep)
        st.rerun()

def run_search(query='',method='combined'):
    return search_jobs(db.get_jobs(),db.get_profile(uid),
        [jid for jid,action in db.get_feedback(uid).items() if action=='hidden'],query,method)

def show_omissions(result):
    if result.get('omitted'):
        with st.expander('Why some roles are excluded'):
            st.caption('Roles with missing eligibility details are excluded. Your filters are never changed automatically.')
            for reason,count in result['omitted'].items():
                st.write(f'{reason.title()}: {count}')

def cards(results,prefix,empty='No internships meet your current preferences. Try changing your filters in Profile.'):
    if not results:
        st.info(empty)
    for job in results:
        with st.container(border=True):
            st.subheader(job['title'])
            st.write(f"**{job['company']}** · {(job['work_mode'] or 'Arrangement not stated').title()} · {job['location'] or 'Location not stated'}")
            if job['required_skills']:
                st.write('**Matching skills:** '+(', '.join(job.get('matching_skills',[])) or 'None'))
                st.write('**Skills to learn:** '+(', '.join(job.get('missing_skills',[])) or 'No listed gaps'))
            else:
                st.caption('Required skills not specified in the listing.')
            if not job['eligible_graduation_years']:
                st.warning('Graduation eligibility unverified — check the original listing.')
            with st.expander('Role details'):
                st.write(job['description'])
                years=job['eligible_graduation_years']
                st.caption('Graduation year: '+('accepted' if years and profile.graduation_year in years else 'not verified for your profile'))
                st.caption(f"Last checked: {job['last_checked_at']}. Check full requirements on the original listing.")
                if (date.today()-date.fromisoformat(job['last_checked_at'])).days>7:
                    st.caption('This listing needs an availability recheck.')
            a,b,c=st.columns([2,1,1])
            a.link_button('View listing ↗',job['source_url'],use_container_width=True)
            saved=feedback.get(job['id'])=='saved'
            if b.button('Unsave' if saved else 'Save',key=f'{prefix}_s_{job["id"]}',use_container_width=True):
                db.set_feedback(uid,job['id'],None if saved else 'saved')
                st.rerun()
            if c.button('Hide',key=f'{prefix}_h_{job["id"]}',use_container_width=True):
                db.set_feedback(uid,job['id'],'hidden')
                st.rerun()

if page=='Profile':
    st.title('Your profile')
    from resume_profile import upload_resume
    resume=db.get_resume(uid)
    with st.container(border=True):
        st.subheader('Resume')
        st.caption('Upload a PDF, DOCX or TXT (up to 5 MB). Gemini extracts your skills and profile. A new resume replaces all previous skills, including skills you added yourself.')
        if resume:
            st.write('**Current resume:** '+resume['resume_name'])
            saved_resume=db.get_resume(uid,include_data=True)
            st.download_button('Download latest resume',saved_resume['resume_data'],
                file_name=resume['resume_name'],mime=resume['resume_mime'])
        upload=st.file_uploader('Upload resume',type=['pdf','docx','txt'],key='resume_upload',
            help='Your resume is sent to Gemini for extraction and saved privately to your account.')
        if st.button('Create profile from resume',type='primary',disabled=upload is None):
            def charge_resume():
                used=st.session_state.get('api_calls',0)
                if used>=20:
                    raise ValueError('The session AI request limit has been reached. Your current profile was kept.')
                st.session_state.api_calls=used+1
            try:
                with st.spinner('Reading your resume with Gemini…'):
                    extracted=upload_resume(uid,upload.name,upload.getvalue(),charge=charge_resume)
                for key in ('chat_results','pending','last_query'):
                    st.session_state.pop(key,None)
                st.session_state.resume_success=True
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if st.session_state.pop('resume_success',False):
            st.success('Resume saved and profile updated. You can add more skills below or open Matches.')
    # Reload after resume replacement; manual edits always start from the newest skills.
    profile=db.get_profile(uid)
    with st.form('profile'):
        skills=st.text_input('Skills',value=', '.join(profile.skills),placeholder='Python, SQL, JavaScript',max_chars=2000,
            help='Separate skills with commas. You can add skills here. Uploading a new resume resets this list to its extracted skills.')
        interests=st.text_area('Interests',value=profile.interests,placeholder='Backend development, data analysis…',max_chars=1000)
        left,right=st.columns(2)
        year=left.number_input('Graduation year',2020,2040,profile.graduation_year)
        locations=right.text_input('Preferred locations',value=', '.join(profile.preferred_locations),
            placeholder='Bengaluru, India',max_chars=1500,help='Separate cities or countries with commas. Leave blank for any location.')
        remote=st.checkbox('Remote roles only',value=profile.remote_only)
        allow_unknown=st.checkbox('Include roles with unstated graduation eligibility',value=profile.allow_unknown_graduation,
            help='Off by default. These roles are marked unverified. Known graduation-year mismatches are still excluded.')
        if st.form_submit_button('Save profile',type='primary'):
            try:
                db.save_profile(uid,Profile(skills=skills.split(','),interests=interests,graduation_year=int(year),
                    remote_only=remote,preferred_locations=locations.split(','),allow_unknown_graduation=allow_unknown))
                for key in ('chat_results','pending'):
                    st.session_state.pop(key,None)
                st.session_state.profile_saved=True
                st.rerun()
            except ValidationError:
                st.error('Check your profile entries. Use up to 40 skills and 15 locations, each under 100 characters.')
    if st.session_state.pop('profile_saved',False):
        st.success('Profile saved. Open Matches to find internships.')
    if remote:
        st.caption('For remote roles, include your country in Preferred locations.')

elif page=='Matches':
    st.title('Find internships')
    if not profile.skills and not profile.interests:
        st.info('Add your skills and interests in Profile for more useful matches.')
    with st.form('search'):
        query=st.text_input('Role or area of interest',value=st.session_state.get('last_query',''),
            placeholder='e.g. Python backend internship',max_chars=1000)
        with st.expander('Search options'):
            method=st.selectbox('Search method',options=['combined','semantic','keyword'],
                format_func=lambda x:{'combined':'Recommended: meaning + skills','semantic':'Meaning only','keyword':'Skill keywords only'}[x])
        submitted=st.form_submit_button('Find matches',type='primary')
    if submitted:
        st.session_state.method=method
        st.session_state.last_query=query
    if submitted or 'last_query' in st.session_state:
        try:
            with st.spinner('Finding matches…'):
                result=run_search(st.session_state.last_query,st.session_state.get('method','combined'))
            st.caption(f"{len(result['results'])} matches shown · {result['eligible_count']} eligible roles")
            show_omissions(result)
            if not result['results'] and result['omitted'].get('missing graduation eligibility'):
                st.info('Some roles omit graduation requirements. To see them with an unverified label, enable “Include roles with unstated graduation eligibility” in Profile.')
            cards(result['results'],'matches')
        except (ValueError,OSError):
            st.error('Semantic search is not ready. Select Skill keywords only in Search options, or run python embeddings.py to rebuild the index.')
    if not jobs:
        st.error('No listings loaded. Run python import_jobs.py to load the collection.')

elif page=='Saved':
    st.title('Saved internships')
    saved_jobs=[]
    for job in jobs:
        if feedback.get(job['id'])=='saved':
            saved_jobs.append({**job,'matching_skills':sorted(set(profile.skills)&set(job['required_skills'] or [])),
                'missing_skills':sorted(set(job['required_skills'] or [])-set(profile.skills))})
    cards(saved_jobs,'saved','No saved internships yet. Save a role from Matches.')
    with st.expander('Hidden internships'):
        hidden_jobs=[j for j in jobs if feedback.get(j['id'])=='hidden']
        if not hidden_jobs:
            st.caption('No hidden internships.')
        for job in hidden_jobs:
            st.write(f"{job['title']} — {job['company']}")
            if st.button('Restore',key=f'restore_{job["id"]}'):
                db.set_feedback(uid,job['id'],None)
                st.rerun()

elif page=='Chat':
    st.title('Internship assistant')
    st.caption('Ask for internships or change your location preferences.')
    api_key,model,config_error=chat_config()
    def charge():
        used=st.session_state.get('api_calls',0)
        if used>=20:
            raise ValueError('The chat session limit has been reached. You can still search in Matches.')
        st.session_state.api_calls=used+1
    agent=None
    if config_error:
        st.warning(config_error)
    else:
        try:
            agent=Agent(uid,api_key,run_search,charge=charge,model=model)
        except Exception as error:
            st.error(provider_error(error))
    for message in st.session_state.get('messages',[]):
        with st.chat_message(message['role']):
            st.write(message['text'])
    def accept(outcome):
        st.session_state.setdefault('messages',[]).append({'role':'assistant','text':outcome['text']})
        st.session_state.chat_results=outcome.get('results',[])
        if outcome.get('pending'):
            st.session_state.pending=outcome['pending']
        st.rerun()
    if 'pending' in st.session_state:
        pending=st.session_state.pending
        args=next(PreferenceArgs.model_validate(call.args or {}) for call in pending['calls'] if call.name=='update_preferences')
        with st.container(border=True):
            st.write('**Update your preferences?**')
            new_remote=profile.remote_only if args.remote_only is None else args.remote_only
            new_locations=profile.preferred_locations if args.preferred_locations is None else args.preferred_locations
            st.write('Work mode: '+('Remote only' if new_remote else 'Any arrangement'))
            st.write('Locations: '+(', '.join(new_locations).title() or 'Any location'))
            if args.add_skills or args.remove_skills:
                if args.add_skills:
                    st.write('Add skills: '+', '.join(args.add_skills))
                if args.remove_skills:
                    st.write('Remove skills: '+', '.join(args.remove_skills))
                st.write('Skills after confirmation: '+(', '.join(preference_skills(profile.skills,args)) or 'None'))
            a,b=st.columns(2)
            if a.button('Confirm change',disabled=agent is None,type='primary'):
                st.session_state.pop('pending')
                with st.spinner('Updating preferences…'):
                    accept(agent.resume(pending,True))
            if b.button('Cancel',disabled=agent is None):
                st.session_state.pop('pending')
                with st.spinner('Cancelling…'):
                    accept(agent.resume(pending,False))
    if st.session_state.get('api_calls',0)>=20:
        st.info('Chat session limit reached. Use Matches to continue searching.')
    message=st.chat_input('e.g. Find Python internships',disabled=agent is None or 'pending' in st.session_state or st.session_state.get('api_calls',0)>=20,max_chars=2000)
    if message:
        st.session_state.setdefault('messages',[]).append({'role':'user','text':message})
        with st.spinner('Thinking…'):
            accept(agent.start(message))
    if st.session_state.get('chat_results'):
        current={j['id']:j for j in db.get_jobs()}
        visible=[j for j in st.session_state.chat_results if j['id'] in current and not exclusion(
            current[j['id']],db.get_profile(uid),{k for k,v in db.get_feedback(uid).items() if v=='hidden'})]
        cards(visible,'chat')
