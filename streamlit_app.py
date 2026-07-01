import streamlit as st

from storage.project_manager import ProjectManager

from ui.sidebar import Sidebar
from ui.connection_form import ConnectionForm
from ui.chat import ChatUI

st.set_page_config(page_title="Smart DB Agent", layout="wide")

if "project_manager" not in st.session_state:

    st.session_state.project_manager = ProjectManager()

if "show_connection_form" not in st.session_state:

    st.session_state.show_connection_form = False

pm = st.session_state.project_manager

Sidebar(pm).render()

ConnectionForm(pm).render()

ChatUI(pm).render()
