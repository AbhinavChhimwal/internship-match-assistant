from datetime import date
import streamlit as st
import db
from catalog_admin import CSV_PATH,add_job,rebuild_index,require_admin,export_catalog
from cloud_storage import StorageUnavailable
from schemas import Job

def render_admin(uid):
    require_admin(uid)
    st.title('Admin dashboard')
    notice=st.session_state.pop('catalog_notice',None)
    if notice is True:
        st.success('Internship saved and available in search.')
    elif notice is False:
        st.warning('Internship saved. The search index needs rebuilding below; keyword search remains available.')
    jobs=db.get_jobs()
    a,b=st.columns(2)
    a.metric('Internships',len(jobs))
    b.metric('Active',sum(j['is_active'] for j in jobs))
    st.subheader('Add an internship')
    with st.form('add_internship',clear_on_submit=True):
        title=st.text_input('Job title',max_chars=180)
        company=st.text_input('Company',max_chars=100)
        url=st.text_input('Original listing URL')
        description=st.text_area('Description',max_chars=1600)
        skills=st.text_input('Required skills',help='Separate with commas. Leave blank if not stated.')
        a,b=st.columns(2)
        mode=a.selectbox('Work arrangement',['Not stated','onsite','hybrid','remote'])
        location=b.text_input('Display location',placeholder='Bengaluru, India')
        places=st.text_input('Compatible cities / countries',placeholder='Bengaluru, India',
            help='Use only locations supported by the listing. Remote does not mean worldwide.')
        years=st.text_input('Eligible graduation years',placeholder='2027, 2028',
            help='Leave blank if the listing does not specify. Never use the internship year as graduation eligibility.')
        checked=st.date_input('Last verified',value=date.today(),max_value=date.today())
        active=st.checkbox('Accepting applications',value=True)
        submitted=st.form_submit_button('Save internship',type='primary')
    if submitted:
        try:
            job=Job(source_url=url.strip(),title=title.strip(),company=company.strip(),description=description.strip(),
                required_skills=[s.strip() for s in skills.split(',') if s.strip()] or None,
                work_mode=None if mode=='Not stated' else mode,location=location.strip() or None,
                compatible_locations=[s.strip() for s in places.split(',') if s.strip()] or None,
                eligible_graduation_years=[int(s.strip()) for s in years.split(',') if s.strip()] or None,
                last_checked_at=checked,is_active=active)
            with st.spinner('Saving listing and updating search…'):
                outcome=add_job(uid,job)
            st.session_state.catalog_notice=outcome['indexed']
            st.rerun()
        except (ValueError,PermissionError) as error:
            st.error(str(error))
        except StorageUnavailable as error:
            st.error(str(error))
        except OSError:
            st.error('Could not write the catalog. Check that data/jobs.csv is writable and not open in Excel.')
    with st.expander('Manage collection'):
        st.download_button('Download jobs.csv',export_catalog(uid),file_name='jobs.csv',mime='text/csv')
        if st.button('Rebuild search index'):
            try:
                with st.spinner('Rebuilding search…'):
                    rebuild_index(uid)
                st.success('Search index rebuilt.')
            except Exception:
                st.error('Index rebuild failed. Check the local embedding model setup.')
        st.dataframe([{'Title':j['title'],'Company':j['company'],'Location':j['location'],
            'Graduation years':', '.join(map(str,j['eligible_graduation_years'] or [])) or 'Not stated',
            'Active':j['is_active'],'Source':j['source_url']} for j in db.get_jobs()],hide_index=True,use_container_width=True)
