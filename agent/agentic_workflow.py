from storage.checkpointer import checkpointer

from langchain_core.messages import HumanMessage, AIMessage

from utils.model_loader import ModelLoader
from prompt_library.prompt import (
    INTENT_DETECTION_PROMPT,
    IntentDetectionOutput,
    QUERY_GENERATION_PROMPT,
    QueryGenerationOutput,
)

from langgraph.graph import StateGraph, START, END
from State.DBState import AgentState

from connectors.manager import connection_manager

from tools.database_tools import execute_query, get_schema

class GraphBuilder:

    def __init__(self, model_provider: str = "groq"):

        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()

        self.tools = []

        self.execute_query_tool = execute_query
        self.get_schema_tool = get_schema

        self.tools.extend([
        self.execute_query_tool,
            self.get_schema_tool,
        ])

        self.llm_with_tools = self.llm.bind_tools(tools=self.tools)
        self.graph = None

    def intent_detection_node(self, state: AgentState):
        structured_llm = self.llm.with_structured_output(IntentDetectionOutput)
        chain = INTENT_DETECTION_PROMPT | structured_llm
        query = state.user_query

        if state.messages:
            last_message = state.messages[-1]

            if isinstance(last_message, HumanMessage):
                query = last_message.content

        result = chain.invoke(
            {
                "user_query": query
            }
        )

        print(f"Identified Intent: {result.identified_intent.value}")

        # Return only updated fields
        return {"identified_intent": result.identified_intent.value}

    def query_generation_node(self, state: AgentState):
        structured_llm = self.llm.with_structured_output(QueryGenerationOutput)
        chain = QUERY_GENERATION_PROMPT | structured_llm
        query = state.user_query

        if state.messages:
            last_message = state.messages[-1]

            if isinstance(last_message, HumanMessage):
                query = last_message.content

        result2 = self.llm.invoke(query)

        print(f"LLM Response: {result2.content}")

        result = chain.invoke(
            {
                "user_query": query,
                "intent": state.identified_intent,
                # "db_schema": state.db_schema or None,
            }
        )

        print(f"Generated Query: {result.generated_query}")

        # Return only updated fields [State]
        return {
            "sql_query": result.generated_query,
            "sql_query_intent": result.generated_query.split()[0].upper(),
            "messages": [
                AIMessage(content=result.generated_query)
            ]
        }

    #  Newly Added Nodes for Intent Based Routing and Query Execution
    # TODO : Complete the node logic

    def route_after_generation(self, state: AgentState):

        sql = state.sql_query.strip().upper()

        if sql.startswith("SELECT"):

            return "execute"

        return "end"

    def intent_based_routing_node(self, state: AgentState):
        if state.identified_intent == "SELECT":
            return {"next_node": "select_query_execution"}
        else:
            # Default routing
            return {"next_node": END}



    def select_query_execution_node(self, state: AgentState):

        connector = connection_manager.get_connection(state.connection_name)

        result = connector.execute_query(state.sql_query)

        print(f"Query Execution Result: {result}")

        return {
            "execution_result": result
        }

    def build_graph(self):

        workflow = StateGraph(AgentState)

        workflow.add_node(
            "intent_detection",
            self.intent_detection_node
        )

        workflow.add_node(
            "query_generation",
            self.query_generation_node
        )

        workflow.add_node(
            "select_query_execution",
            self.select_query_execution_node
        )

        workflow.add_edge(
            START,
            "intent_detection"
        )

        workflow.add_edge(
            "intent_detection",
            "query_generation"
        )

        workflow.add_conditional_edges(
            "query_generation",
            self.route_after_generation,
            {
                "execute": "select_query_execution",
                "end": END,
            }
        )

        workflow.add_edge(
            "select_query_execution",
            END
        )

        self.graph = workflow.compile(
            checkpointer=checkpointer
        )

        return self.graph
    
    # def invoke(self, state: AgentState, thread_id: str):

    #     if self.graph is None:
    #         self.build_graph()

    #     config = {
    #             "configurable": {
    #             "thread_id": thread_id
    #         }
    #     }

    #     if state.user_query:

    #         state.messages.append(
    #             HumanMessage(
    #                 content=state.user_query
    #             )
    #         )

    #     return self.graph.invoke(
    #         state,
    #         config=config
    #     )
    
    def get_state(self, thread_id: str):

        if self.graph is None:
            self.build_graph()

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        return self.graph.get_state(config)

    def list_threads(self):

        threads = set()

        for checkpoint in checkpointer.list(None):

            threads.add(
                checkpoint.config["configurable"]["thread_id"]
            )

        return list(threads)

    # def __call__(self):
    #     if self.graph is None:
    #         self.build_graph()

    #     return self.graph
