from langgraph.graph import StateGraph, START, END

from storage.checkpointer import checkpointer

from State.DBState import AgentState

# Nodes
from agent.nodes.user_query_node import UserQueryNode
from agent.nodes.non_database_query_node import NonDatabaseQueryNode
from agent.nodes.schema_fetch_node import SchemaFetchNode
from agent.nodes.sql_generation_node import SQLGenerationNode
from agent.nodes.execute_query_node import ExecuteQueryNode
from agent.nodes.demo_application_node import DemoApplicationNode
from agent.nodes.response_node import ResponseNode


# Routers
from agent.routers.intent_router import IntentRouter
from agent.routers.condition_router import ConditionRouter


class GraphBuilder:

    def __init__(self):

        # Nodes

        self.user_query_node = UserQueryNode()

        self.non_database_query_node = NonDatabaseQueryNode()

        self.schema_fetch_node = SchemaFetchNode()

        self.sql_generation_node = SQLGenerationNode()

        self.execute_query_node = ExecuteQueryNode()

        self.demo_application_node = DemoApplicationNode()
    
        self.response_node = ResponseNode()

        # Routers

        self.intent_router = IntentRouter()

        self.condition_router = ConditionRouter()

    def build_graph(self):

        workflow = StateGraph(AgentState)

        ##################################################
        # Register Nodes
        ##################################################

        workflow.add_node(
            "user_query",
            self.user_query_node
        )

        workflow.add_node(
            "non_db_query",
            self.non_database_query_node
        )

        workflow.add_node(
            "schema_fetch",
            self.schema_fetch_node
        )

        workflow.add_node(
            "generate_sql",
            self.sql_generation_node
        )

        workflow.add_node(
            "execute_query",
            self.execute_query_node
        )

        workflow.add_node(
            "response",
            self.response_node
        )

        workflow.add_node(
            "demo_application",
            self.demo_application_node
        )

        ##################################################
        # Start
        ##################################################

        workflow.add_edge(
            START,
            "user_query"
        )

        ##################################################
        # Intent Routing
        ##################################################

        workflow.add_conditional_edges(
            "user_query",
            self.intent_router,
            {
                "schema_fetch": "schema_fetch",
                "non_db_query": "non_db_query",
            },
        )

        ##################################################
        # Non DB Query
        ##################################################

        workflow.add_edge(
            "non_db_query",
            END
        )

        ##################################################
        # Schema
        ##################################################

        workflow.add_edge(
            "schema_fetch",
            "generate_sql"
        )

        ##################################################
        # SQL Routing
        ##################################################

        workflow.add_conditional_edges(
            "generate_sql",
            self.condition_router,
            {
                "execute": "execute_query",
                "demo": "demo_application",
            },
        )

        ##################################################
        # End
        ##################################################

        workflow.add_edge(
            "execute_query",
            "response"
        )

        workflow.add_conditional_edges(
            "demo_application",
            lambda state: (
                "execute"
                if state.approval
                else "end"
            ),
            {
                "execute": "execute_query",
                "end": END,
            },
        )

        workflow.add_edge(
            "response",
            END
        )

        return workflow.compile(
            checkpointer=checkpointer
        )