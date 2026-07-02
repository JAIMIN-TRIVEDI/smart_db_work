import streamlit as st
import traceback
import datetime

from agent.agentic_workflow import GraphBuilder
from State.DBState import AgentState

from connectors.manager import connection_manager


class ChatUI:

    def __init__(self, project_manager):

        self.project_manager = project_manager

    def render(self):

        project = self.project_manager.get_current_project()

        if project is None:

            st.info("Create or select a project.")

            return

        st.title(project.title)

        st.caption(f"Connected to : {project.database_config.database_type.upper()}")

        st.divider()

        # Display history

        for msg in project.chat_history:

            with st.chat_message(msg["role"]):

                st.markdown(msg["content"])

        prompt = st.chat_input("Ask anything about your database...")

        if prompt:

            self.process_query(project, prompt)

    ##################################################

    def process_query(self, project, prompt):

        project.add_message("user", prompt)

        with st.chat_message("user"):

            st.markdown(prompt)

        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                try:

                    graph = GraphBuilder()

                    print("Project title:", project.title)
                    print("Available connections:", connection_manager.list_connections())

                    connector = project.connector   

                    state = AgentState(
                        user_query=prompt,
                        db_connection=connector
                    )

                    result = graph.invoke(state)

                    if isinstance(result, dict):

                        answer = (
                            result.get("sql_query")
                            or result.get("answer")
                            or str(result)
                        )

                    else:

                        answer = str(result)

                    st.markdown(answer)

                    project.add_message("assistant", answer)

                except Exception:

                    st.code(traceback.format_exc())
