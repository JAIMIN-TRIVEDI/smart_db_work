import streamlit as st

from db_models.database import DatabaseConfig
from connectors.manager import connection_manager


class ConnectionForm:

    def __init__(self, project_manager):

        self.project_manager = project_manager

    def render(self):

        if not st.session_state.show_connection_form:
            return

        st.subheader("Create New Project")

        with st.form("connection_form"):

            project_name = st.text_input("Project Name", placeholder="Company Database")

            db_type = st.selectbox("Database Type", ["mysql", "mongodb"])

            host = st.text_input("Host", value="localhost")

            port = st.number_input(
                "Port",
                value=3306 if db_type == "mysql" else 27017,
            )

            username = st.text_input("Username")

            password = st.text_input("Password", type="password")

            database = st.text_input("Database")

            submitted = st.form_submit_button("Connect")

        if not submitted:
            return

        try:

            config = DatabaseConfig(
                database_type=db_type,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )

            self.project_manager.create_project(project_name, config)

            st.success("Connected Successfully")

            st.session_state.show_connection_form = False

            st.rerun()

        except Exception as e:

            st.error(str(e))
