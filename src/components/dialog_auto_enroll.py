import streamlit as st
from src.database.db import (
    enroll_student_to_subject,
    get_subject_by_code,
    check_enrollment_exists
)
import time


@st.dialog("Quick Enrollment")
def auto_enroll_dialog(subject_code):
    """
    Auto-enrollment dialog triggered by QR code scan (join-code query param).
    Uses centralised db.py helpers — no direct supabase calls.
    """
    student_id = st.session_state.student_data['student_id']

    # FIX: Use centralised helper instead of direct supabase call
    subject = get_subject_by_code(subject_code)
    if not subject:
        st.error('Subject Code not found!')
        if st.button('Close'):
            st.query_params.clear()
            st.rerun()
        return

    # FIX: Use centralised duplicate-check helper
    if check_enrollment_exists(student_id, subject['subject_id']):
        st.info("You're already enrolled!")
        if st.button('Got it!'):
            st.query_params.clear()
            st.rerun()
        return

    st.markdown(f'Would you like to enroll in **{subject["name"]}**?')

    col1, col2 = st.columns(2)

    with col1:
        if st.button('No thanks'):
            st.query_params.clear()
            st.rerun()
    with col2:
        if st.button('Yes enroll now!', type='primary', width='stretch'):
            enroll_student_to_subject(student_id, subject['subject_id'])
            st.success('Joined successfully!')
            st.query_params.clear()
            time.sleep(2)
            st.rerun()
