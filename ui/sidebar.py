import streamlit as st

from storage.project_manager import ProjectManager


class Sidebar:

    def __init__(self, project_manager: ProjectManager):

        self.project_manager = project_manager

    ########################################################

    def render(self):

        with st.sidebar:

            st.title("🗂 Projects")

            st.divider()

            if st.button(
                "➕ New Project",
                use_container_width=True
            ):
                st.session_state.show_connection_form = True

            project = self.project_manager.get_current_project()

            ####################################################
            ## New Chat
            ####################################################

            if project is not None:

                if st.button(
                    "💬 New Chat",
                    use_container_width=True
                ):

                    self.project_manager.create_conversation(
                        project.id,
                        f"Chat {len(project.conversations)+1}"
                    )

                    st.rerun()

            st.divider()

            ####################################################
            ## Projects
            ####################################################

            projects = self.project_manager.list_projects()

            if not projects:

                st.info("No Projects Created")

                return

            for project in projects:

                self.render_project(project)

    ########################################################

    def render_project(self, project):

        expanded = (
            self.project_manager.current_project
            == project.id
        )

        with st.expander(
            project.title,
            expanded=expanded
        ):

            col1, col2 = st.columns([5,1])

            with col1:

                if st.button(
                    "Open",
                    key=f"project_{project.id}",
                    use_container_width=True
                ):

                    self.project_manager.switch_project(
                        project.id
                    )

                    st.rerun()

            with col2:

                if st.button(
                    "🗑",
                    key=f"delete_{project.id}"
                ):

                    self.project_manager.delete_project(
                        project.id
                    )

                    st.rerun()

            ####################################################
            ## Conversations
            ####################################################

            for conversation in project.conversations:

                active = (
                    conversation.id
                    == project.active_conversation
                )

                title = conversation.title

                if active:

                    title = "🟢 " + title

                if st.button(

                    title,

                    key=f"conversation_{conversation.id}",

                    use_container_width=True

                ):

                    self.project_manager.switch_conversation(
                        project.id,
                        conversation.id
                    )

                    st.rerun()