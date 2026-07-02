import streamlit as st
import traceback

from agent.graph import chatbot
from State.DBState import AgentState
from langchain_core.messages import HumanMessage, AIMessage


class ChatUI:

    def __init__(self, project_manager):
        self.project_manager = project_manager

    ########################################################

    def load_messages(self, conversation):

        config = {
            "configurable": {
                "thread_id": conversation.thread_id
            }
        }

        try:

            state = chatbot.get_state(config)

            if state is None:
                return []

            if not state.values:
                return []

            return state.values.get("messages", [])

        except Exception:

            return []

    ########################################################

    def render(self):

        project = self.project_manager.get_current_project()

        if project is None:

            st.info("Create or Select a Project")

            return

        conversation = project.get_active_conversation()

        st.title(project.title)

        st.caption(
            f"Connected to : {project.database_config.database_type.upper()}"
        )

        st.divider()

        #######################################################
        ## Load Chat
        #######################################################

        messages = self.load_messages(conversation)

        for message in messages:

            if isinstance(message, HumanMessage):

                with st.chat_message("user"):

                    st.markdown(message.content)

            elif isinstance(message, AIMessage):

                with st.chat_message("assistant"):

                    st.markdown(message.content)

        #######################################################
        ## Chat Input
        #######################################################

        prompt = st.chat_input(
            "Ask anything about your database..."
        )

        if prompt:

            self.process_query(
                project,
                conversation,
                prompt
            )

    ########################################################

    def process_query(
        self,
        project,
        conversation,
        prompt
    ):

        with st.chat_message("user"):

            st.markdown(prompt)

        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                try:

                    state = AgentState(

                        user_query=prompt,

                        # db_connection=project.connector,

                        connection_name=project.connection_name,

                        project_id=project.id,

                        conversation_id=conversation.id,

                        thread_id=conversation.thread_id

                    )

                    config = {

                        "configurable": {

                            "thread_id": conversation.thread_id

                        }

                    }

                    result = chatbot.invoke(
                        input=state,
                        config=config
                    )

                    answer = ""

                    if isinstance(result, dict):

                        answer = (
                            result.get("sql_query")
                            or result.get("answer")
                            or str(result)
                        )

                    else:

                        answer = str(result)

                    st.markdown(answer)

                except Exception:

                    st.code(traceback.format_exc())