import traceback

import streamlit as st

from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import chatbot
from State.DBState import AgentState
from agent.services.execution_service import ExecutionService
from agent.services.response_service import ResponseService


class ChatUI:

    def __init__(self, project_manager):
        self.project_manager = project_manager

    ########################################################
    # GRAPH CONFIG
    ########################################################

    def _config(self, conversation):
        return {"configurable": {"thread_id": conversation.thread_id}}

    ########################################################
    # LOAD MESSAGES
    ########################################################

    def load_messages(self, conversation):
        try:
            graph_state = chatbot.get_state(self._config(conversation))

            if graph_state is None:
                return []

            if graph_state.values is None:
                return []

            return graph_state.values.get("messages", [])

        except Exception:
            return []

    ########################################################
    # LOAD GRAPH STATE
    ########################################################

    def load_graph_state(self, conversation):
        try:
            graph_state = chatbot.get_state(self._config(conversation))

            if graph_state is None or graph_state.values is None:
                return {}

            return graph_state.values

        except Exception:
            return {}

    ########################################################
    # RENDER CHAT MESSAGES
    ########################################################

    def render_messages(self, conversation):
        messages = self.load_messages(conversation)

        for message in messages:

            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)

            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.markdown(message.content)

    ########################################################
    # NORMALIZE RESULT ROWS
    ########################################################

    @staticmethod
    def _rows_from_result(result):

        if isinstance(result, list):
            return [dict(x) if isinstance(x, dict) else {"value": x} for x in result]

        if isinstance(result, dict):

            for key in (
                "rows",
                "data",
                "records",
                "result",
            ):
                value = result.get(key)

                if isinstance(value, list):
                    return [
                        dict(x) if isinstance(x, dict) else {"value": x} for x in value
                    ]

        return []

    ########################################################
    # SNAPSHOT TABLE
    ########################################################

    def _snapshot_table(self, state, table_name):

        read_state = state.model_copy(deep=False)

        read_state.generated_sql_query = f"SELECT * FROM `{table_name}` LIMIT 100"

        read_state.identified_intent = "SELECT"
        read_state.query_type = "read"
        read_state.requires_approval = False
        read_state.approval = True

        result = ExecutionService().execute(read_state)

        return self._rows_from_result(result)

    ########################################################
    # RENDER DEMO RESULT
    ########################################################

    def _render_demo_result(
        self,
        conversation,
        demo_result,
    ):

        if not demo_result:
            return

        caution = demo_result.get(
            "caution",
            (
                "This is a demo preview. "
                "Review the before and after effect carefully."
            ),
        )

        st.warning(caution)

        before_data = demo_result.get("before", [])
        after_data = demo_result.get("after", [])

        preview_col1, preview_col2 = st.columns(2)

        with preview_col1:
            st.markdown("#### Before")

            if before_data:
                st.dataframe(
                    before_data,
                    width="stretch",
                )
            else:
                st.info("No before rows available.")

        with preview_col2:
            st.markdown("#### After")

            if after_data:
                st.dataframe(
                    after_data,
                    width="stretch",
                )
            else:
                st.info("No after rows available.")

        extra_info = demo_result.get("summary")

        if extra_info:
            st.caption(extra_info)

    ########################################################
    # PERSISTED QUERY HISTORY
    ########################################################

    READ_INTENTS = {
        "SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN",
        "ANALYTICS", "AGGREGATION", "REPORT",
        "SCHEMA_INFO", "DATABASE_INFO",
    }

    @classmethod
    def _is_read_turn(cls, turn):
        if turn.get("is_read") is True:
            return True
        if str(turn.get("query_type") or "").lower() == "read":
            return True
        return str(turn.get("identified_intent") or "").upper() in cls.READ_INTENTS

    def _render_saved_turn(self, turn):
        with st.chat_message("user"):
            st.markdown(turn.get("user_input") or "")

        st.markdown("#### Generated Query")
        st.code(turn.get("generated_sql_query") or "", language="sql")

        if self._is_read_turn(turn):
            st.markdown("#### Execution Result")
            result = turn.get("execution_result")
            rows = self._rows_from_result(result)
            if rows:
                st.dataframe(rows, width="stretch")
            elif result is not None:
                st.write(result)
            else:
                st.info("No result was returned.")
            st.divider()
            return

        st.markdown("#### Query Plan")
        c1, c2, c3 = st.columns(3)
        confidence = turn.get("query_confidence")
        c1.metric("Confidence", f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a")
        c2.metric("Risk", turn.get("query_risk_level") or "n/a")
        c3.metric("Approval", "Required" if turn.get("requires_approval") else "Not required")
        if turn.get("query_reasoning"):
            st.caption(turn["query_reasoning"])

        demo = turn.get("demo_result")
        if demo:
            st.markdown("#### Demo Preview")
            self._render_demo_result(None, demo)

        result = turn.get("execution_result")
        if result is not None:
            st.markdown("#### Execution Result")
            rows = self._rows_from_result(result)
            st.dataframe(rows, width="stretch") if rows else st.write(result)
        st.divider()

    def render_query_history(self, conversation, exclude_latest=True):
        state = self.load_graph_state(conversation)
        history = list(state.get("query_history") or [])
        if exclude_latest and history:
            history = history[:-1]
        for turn in history:
            self._render_saved_turn(turn)

    ########################################################
    # RENDER QUERY WORKBENCH
    ########################################################

    def render_query_workbench(self, conversation):

        latest_state = self.load_graph_state(conversation)

        if not latest_state:
            return

        generated_sql = latest_state.get("generated_sql_query")

        if not generated_sql:
            return

        intent = (latest_state.get("identified_intent") or "").upper()
        query_type = (latest_state.get("query_type") or "").lower()
        is_direct_read = query_type == "read" or intent in self.READ_INTENTS

        # Read queries intentionally show only generated query + execution result.
        if is_direct_read:
            st.markdown("#### Generated Query")
            st.code(generated_sql, language="sql")
            st.markdown("#### Execution Result")
            execution_result = latest_state.get("execution_result")
            rows = self._rows_from_result(execution_result)
            if rows:
                st.dataframe(rows, width="stretch")
            elif execution_result is not None:
                st.write(execution_result)
            else:
                st.info("The query was generated but no result was returned.")
            return

        ####################################################
        # QUERY PLAN
        ####################################################

        st.divider()
        st.subheader("Query Plan")

        st.code(
            generated_sql,
            language="sql",
        )

        confidence = latest_state.get("query_confidence")

        risk_level = latest_state.get("query_risk_level")

        query_reasoning = latest_state.get("query_reasoning")

        requires_approval = latest_state.get("requires_approval")


        ####################################################
        # QUERY METRICS
        ####################################################

        summary_col1, summary_col2, summary_col3 = st.columns(3)

        summary_col1.metric(
            "Confidence",
            (f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"),
        )

        summary_col2.metric(
            "Risk",
            risk_level or "n/a",
        )

        summary_col3.metric(
            "Approval",
            ("Required" if requires_approval else "Not required"),
        )

        if query_reasoning:
            st.caption(query_reasoning)

        ####################################################
        # READ QUERY RESULT
        ####################################################

        if is_direct_read:

            st.divider()
            st.subheader("Result")

            execution_result = latest_state.get("execution_result")

            rows = self._rows_from_result(execution_result)

            if rows:
                st.dataframe(
                    rows,
                    width="stretch",
                )

            elif execution_result is not None:
                st.write(execution_result)

            else:
                st.info("The query was generated but no result " "was returned.")

            return

        ####################################################
        # WRITE / MODIFY QUERY DEMO SECTION
        #
        # IMPORTANT:
        # This section is ALWAYS visible.
        # It does NOT depend on demo_result existing.
        ####################################################

        st.divider()
        st.subheader("Demo Preview")

        st.info(
            "Run the generated query on demo data first "
            "to inspect its expected before/after effect. "
            "This preview must not modify the actual database."
        )

        preview_visible_key = f"show_demo_preview_{conversation.id}"

        demo_cache_key = f"demo_result_{conversation.id}"

        demo_error_key = f"demo_error_{conversation.id}"

        ####################################################
        # GET GRAPH DEMO RESULT
        ####################################################

        graph_demo_result = latest_state.get("demo_result")

        if graph_demo_result:
            st.session_state[demo_cache_key] = graph_demo_result

        ####################################################
        # DEMO BUTTON
        #
        # ALWAYS SHOWN FOR NON-READ QUERIES
        ####################################################

        if st.button(
            "Run on Demo Data",
            key=f"demo_btn_{conversation.id}",
            width="stretch",
        ):

            st.session_state[preview_visible_key] = True

            st.session_state.pop(
                demo_error_key,
                None,
            )

            ################################################
            # First use demo_result already generated
            # by graph.
            ################################################

            if graph_demo_result:

                st.session_state[demo_cache_key] = graph_demo_result

            else:

                ################################################
                # No demo result exists.
                #
                # Keep UI visible and report backend problem.
                # Do NOT silently remove preview.
                ################################################

                st.session_state[demo_error_key] = (
                    "The demo preview backend did not return "
                    "`demo_result`. The preview UI is working, "
                    "but the graph/demo service must generate "
                    "before and after data."
                )

            st.rerun()

        ####################################################
        # DISPLAY DEMO PREVIEW
        ####################################################

        if st.session_state.get(
            preview_visible_key,
            False,
        ):

            cached_demo_result = st.session_state.get(demo_cache_key)

            demo_error = st.session_state.get(demo_error_key)

            if cached_demo_result:

                self._render_demo_result(
                    conversation,
                    cached_demo_result,
                )

            elif demo_error:

                st.error(demo_error)

                st.warning(
                    "The generated query has NOT been run " "on the actual database."
                )

            else:

                st.info("No demo preview data is available yet.")

        ####################################################
        # LIVE DATABASE EXECUTION SECTION
        ####################################################

        st.divider()
        st.subheader("Actual Database Execution")

        affected_tables = latest_state.get("affected_tables") or []

        risk_text = risk_level if risk_level else "Unknown"

        caution_message = latest_state.get("impact_summary")

        if not caution_message:

            table_text = (
                ", ".join(affected_tables)
                if affected_tables
                else "one or more database objects"
            )

            caution_message = (
                f"This query may modify {table_text}. "
                f"Current risk level: {risk_text}. "
                "Changes will be applied to the connected "
                "live database."
            )

        st.warning(caution_message)

        ####################################################
        # CONFIRMATION CHECKBOX
        ####################################################

        confirm_key = f"confirm_execute_{conversation.id}"

        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        confirmed = st.checkbox(
            (
                "I understand the impact and want to run "
                "this query on the actual database."
            ),
            value=st.session_state[confirm_key],
            key=f"confirm_box_{conversation.id}",
        )

        st.session_state[confirm_key] = confirmed

        ####################################################
        # ACTUAL EXECUTION BUTTON
        ####################################################

        if st.button(
            "Run on Actual Database",
            key=f"execute_actual_{conversation.id}",
            width="stretch",
            disabled=not confirmed,
            type="primary",
        ):

            try:

                execution_state = AgentState.model_validate(latest_state)

                execution_state.approval = True

                execution_state.generated_sql_query = generated_sql

                ################################################
                # SNAPSHOT BEFORE LIVE EXECUTION
                ################################################

                pre_rows = {}

                for table_name in affected_tables:

                    try:
                        pre_rows[table_name] = self._snapshot_table(
                            execution_state,
                            table_name,
                        )

                    except Exception as exc:
                        pre_rows[table_name] = {"error": str(exc)}

                ################################################
                # EXECUTE LIVE QUERY
                ################################################

                execution_result = ExecutionService().execute(execution_state)

                execution_state.execution_result = execution_result

                ################################################
                # SNAPSHOT AFTER LIVE EXECUTION
                ################################################

                post_rows = {}

                for table_name in affected_tables:

                    try:
                        post_rows[table_name] = self._snapshot_table(
                            execution_state,
                            table_name,
                        )

                    except Exception as exc:
                        post_rows[table_name] = {"error": str(exc)}

                ################################################
                # BUILD RESPONSE
                ################################################

                response = ResponseService().build_response(execution_state)

                ################################################
                # SAVE RESULTS IN SESSION STATE
                ################################################

                st.session_state[f"manual_execution_result_{conversation.id}"] = (
                    execution_result
                )

                st.session_state[f"manual_execution_response_{conversation.id}"] = (
                    response.content
                )

                st.session_state[f"pre_execution_rows_{conversation.id}"] = pre_rows

                st.session_state[f"post_execution_rows_{conversation.id}"] = post_rows

                ################################################
                # RESET CONFIRMATION
                ################################################

                st.session_state[confirm_key] = False

                st.success("Query executed on the live database.")

                st.rerun()

            except Exception:

                st.error("Live database execution failed.")

                st.code(traceback.format_exc())

        ####################################################
        # MANUAL EXECUTION RESPONSE
        ####################################################

        manual_response = st.session_state.get(
            f"manual_execution_response_{conversation.id}"
        )

        if manual_response:

            st.divider()
            st.subheader("Execution Response")

            st.markdown(manual_response)

        ####################################################
        # BEFORE LIVE EXECUTION
        ####################################################

        pre_rows = st.session_state.get(
            f"pre_execution_rows_{conversation.id}",
            {},
        )

        ####################################################
        # AFTER LIVE EXECUTION
        ####################################################

        post_rows = st.session_state.get(
            f"post_execution_rows_{conversation.id}",
            {},
        )

        ####################################################
        # SHOW LIVE BEFORE / AFTER
        ####################################################

        if pre_rows or post_rows:

            st.divider()
            st.subheader("Actual Database Before / After")

            all_tables = set(list(pre_rows.keys()) + list(post_rows.keys()))

            for table_name in all_tables:

                st.markdown(f"### {table_name}")

                before_col, after_col = st.columns(2)

                with before_col:

                    st.markdown("#### Before")

                    before_value = pre_rows.get(
                        table_name,
                        [],
                    )

                    if isinstance(before_value, list):

                        if before_value:
                            st.dataframe(
                                before_value,
                                width="stretch",
                            )
                        else:
                            st.info("No rows before execution.")

                    else:
                        st.warning(
                            before_value.get(
                                "error",
                                "Unable to load before rows.",
                            )
                        )

                with after_col:

                    st.markdown("#### After")

                    after_value = post_rows.get(
                        table_name,
                        [],
                    )

                    if isinstance(after_value, list):

                        if after_value:
                            st.dataframe(
                                after_value,
                                width="stretch",
                            )
                        else:
                            st.info("No rows after execution.")

                    else:
                        st.warning(
                            after_value.get(
                                "error",
                                "Unable to load after rows.",
                            )
                        )

    ########################################################
    # MAIN RENDER
    ########################################################

    def render(self):

        project = self.project_manager.get_current_project()

        if project is None:

            st.info("Create or Select a Project")

            return

        conversation = project.get_active_conversation()

        st.title(project.title)

        st.caption("Connected to : " f"{project.database_config.database_type.upper()}")

        st.divider()

        ####################################################
        # CHAT HISTORY
        ####################################################

        graph_state = self.load_graph_state(conversation)
        if graph_state.get("query_history"):
            self.render_query_history(conversation, exclude_latest=True)
        else:
            self.render_messages(conversation)

        ####################################################
        # QUERY WORKBENCH
        ####################################################

        self.render_query_workbench(conversation)

        ####################################################
        # CHAT INPUT
        ####################################################

        prompt = st.chat_input("Ask anything about your database...")

        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)

            self.process_query_stream(
                project,
                conversation,
                prompt,
            )

            st.rerun()

    ########################################################
    # STREAM QUERY PROGRESS
    ########################################################

    def process_query_stream(self, project, conversation, prompt):
        labels = {
            "user_query": "Understanding your request...",
            "schema_fetch": "Retrieving relevant schema...",
            "generate_sql": "Generating database query...",
            "query_critic": "Validating generated query...",
            "investigation": "Investigating database values safely...",
            "condition_route": "Choosing safe execution path...",
            "execute_query": "Executing read query...",
            "demo_application": "Preparing demo preview...",
            "response": "Preparing result...",
            "finalize_query": "Saving query turn...",
        }

        try:
            with st.status("Processing query...", expanded=True) as status:
                for update in chatbot.stream(
                    {
                        "messages": [HumanMessage(content=prompt)],
                        "project_id": project.id,
                        "conversation_id": conversation.id,
                        "thread_id": conversation.thread_id,
                        "connection_name": project.connection_name,
                        "database_config": project.database_config.model_dump(),
                    },
                    config=self._config(conversation),
                    stream_mode="updates",
                ):
                    for node_name, node_update in update.items():
                        st.write(labels.get(node_name, f"Running {node_name}..."))
                        if node_name == "generate_sql" and isinstance(node_update, dict):
                            sql = node_update.get("generated_sql_query")
                            if sql:
                                st.code(sql, language="sql")
                status.update(label="Query processing complete", state="complete", expanded=False)

        except Exception:
            st.error("Failed to process the query.")
            st.code(traceback.format_exc())

    ########################################################
    # PROCESS QUERY
    ########################################################

    def process_query(
        self,
        project,
        conversation,
        prompt,
    ):

        try:

            chatbot.invoke(
                {
                    "messages": [HumanMessage(content=prompt)],
                    "project_id": project.id,
                    "conversation_id": (conversation.id),
                    "thread_id": (conversation.thread_id),
                    "connection_name": (project.connection_name),
                    "database_config": (project.database_config.model_dump()),
                },
                config=self._config(conversation),
            )

            st.session_state[f"last_graph_state_{conversation.id}"] = (
                self.load_graph_state(conversation)
            )

            ################################################
            # CLEAR OLD UI STATE FOR NEW QUERY
            ################################################

            st.session_state.pop(
                f"show_demo_preview_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"demo_result_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"demo_error_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"confirm_execute_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"manual_execution_result_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"manual_execution_response_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"pre_execution_rows_{conversation.id}",
                None,
            )

            st.session_state.pop(
                f"post_execution_rows_{conversation.id}",
                None,
            )

        except Exception:

            st.error("Failed to process the query.")

            st.code(traceback.format_exc())
