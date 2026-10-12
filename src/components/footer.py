import streamlit as st


def footer_home():
    st.markdown("""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
            <p style="font-weight:500; color:#E0F2EE; font-size:0.9rem;">AI Class &bull; Intelligent Classroom Attendance System</p>
        </div>
    """, unsafe_allow_html=True)


def footer_dashboard():
    st.markdown("""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
            <p style="font-weight:500; color:#666; font-size:0.9rem;">AI Class &bull; Intelligent Classroom Attendance System</p>
        </div>
    """, unsafe_allow_html=True)
