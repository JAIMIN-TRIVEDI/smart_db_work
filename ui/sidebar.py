import streamlit as st

from storage.project_manager import ProjectManager


class Sidebar:

    def __init__(self, project_manager: ProjectManager):

        self.project_manager = project_manager

    def render(self):

        with st.sidebar:

            st.title("🗂 Projects")

            st.divider()

            # Create Project Button
            if st.button("➕ New Project", use_container_width=True):
                st.session_state.show_connection_form = True

            st.divider()

            projects = self.project_manager.list_projects()

            if not projects:

                st.info("No projects created.")

                return

            for project in projects:

                self.render_project(project)

    #####################################################

    def render_project(self, project):

        col1, col2 = st.columns([6, 1])

        active = self.project_manager.current_project == project.id

        title = project.title

        if active:
            title = "🟢 " + title

        with col1:

            if st.button(
                title,
                key=f"select_{project.id}",
                use_container_width=True,
            ):

                self.project_manager.switch_project(project.id)

                st.rerun()

        with col2:

            if st.button(
                "🗑",
                key=f"delete_{project.id}",
            ):

                self.project_manager.delete_project(project.id)

                st.rerun()
