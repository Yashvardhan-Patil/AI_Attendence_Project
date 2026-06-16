import streamlit as st
from PIL import Image


@st.dialog("Capture photos")
def add_photos_dialog():
    st.write('Take live classroom photos to scan for attendance')

    cam_photo = st.camera_input('Take Snapshot', key='dialog_cam')
    if cam_photo:
        st.session_state.attendance_images.append(Image.open(cam_photo))
        st.toast('Photo Captured')
        st.rerun()

    st.divider()
    if st.button('Done', type='primary', width='stretch'):
        st.rerun()
