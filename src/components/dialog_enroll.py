import streamlit as st
from src.database.db import (
    enroll_student_to_subject,
    get_subject_by_code,
    check_enrollment_exists
)
import time


@st.dialog("Enroll in Subject")
def enroll_dialog():
    """
    Dialog for students to manually enroll in a subject using a join code.
    Uses centralised db.py helpers — no direct supabase calls.
    """
    st.write('Enter the subject code provided by your teacher to enroll')
    join_code = st.text_input('Subject Code', placeholder='Eg. CS101')

    if st.button('Enroll now', type='primary', width='stretch'):
        if join_code:
            # FIX: Use centralised helper instead of direct supabase call
            subject = get_subject_by_code(join_code)
            if subject:
                student_id = st.session_state.student_data['student_id']

                # FIX: Use centralised duplicate-check helper
                if check_enrollment_exists(student_id, subject['subject_id']):
                    st.warning('You are already enrolled in this program')
                else:
                    enroll_student_to_subject(student_id, subject['subject_id'])
                    st.success('Successfully enrolled!')
                    time.sleep(1)
                    st.rerun()
            else:
                st.error('Subject code not found!')
        else:
            st.warning('Please enter a subject code')