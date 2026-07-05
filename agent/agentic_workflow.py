from langgraph.graph import StateGraph, START, END

from storage.checkpointer import checkpointer
from State.DBState import AgentState

# Nodes
from agent.nodes.user_query_node import UserQueryNode
from agent.nodes.non_database_query_node import NonDatabaseQueryNode
from agent.nodes.schema_fetch_node import SchemaFetchNode
from agent.nodes.sql_generation_node import SQLGenerationNode
from agent.nodes.query_critic_node import QueryCriticNode
from agent.nodes.investigation_node import InvestigationNode
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

        self.query_critic_node = QueryCriticNode()

        self.investigation_node = InvestigationNode()

        self.execute_query_node = ExecuteQueryNode()

        self.demo_application_node = DemoApplicationNode()

        self.response_node = ResponseNode()

        # Routers
        self.intent_router = IntentRouter()

        self.condition_router = ConditionRouter()

    ######################################################
    # Critic Router
    ######################################################

    @staticmethod
    def _critic_router(
        state: AgentState,
    ):
        decision = (state.critic_status or "ACCEPT").upper()

        print("=" * 80)
        print("CRITIC ROUTER")
        print("Decision:", decision)
        print(
            "Refinement count:",
            state.refinement_count,
        )

        if decision == "INVESTIGATE":
            return "investigate"

        if decision == "REVISE":
            return "revise"

        return "continue"

    ######################################################
    # Demo Router
    ######################################################

    @staticmethod
    def _demo_router(
        state: AgentState,
    ):
        if state.approval is True:
            return "execute"

        return "end"

    ######################################################
    # Build Graph
    ######################################################

    def build_graph(self):

        workflow = StateGraph(AgentState)

        ##################################################
        # Register Nodes
        ##################################################

        workflow.add_node(
            "user_query",
            self.user_query_node,
        )

        workflow.add_node(
            "non_db_query",
            self.non_database_query_node,
        )

        workflow.add_node(
            "schema_fetch",
            self.schema_fetch_node,
        )

        workflow.add_node(
            "generate_sql",
            self.sql_generation_node,
        )

        workflow.add_node(
            "query_critic",
            self.query_critic_node,
        )

        workflow.add_node(
            "investigation",
            self.investigation_node,
        )

        workflow.add_node(
            "execute_query",
            self.execute_query_node,
        )

        workflow.add_node(
            "demo_application",
            self.demo_application_node,
        )

        workflow.add_node(
            "response",
            self.response_node,
        )

        ##################################################
        # Start
        ##################################################

        workflow.add_edge(
            START,
            "user_query",
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
        # Non DB
        ##################################################

        workflow.add_edge(
            "non_db_query",
            END,
        )

        ##################################################
        # Schema → Generation
        ##################################################

        workflow.add_edge(
            "schema_fetch",
            "generate_sql",
        )

        ##################################################
        # Generation → Critic
        ##################################################

        workflow.add_edge(
            "generate_sql",
            "query_critic",
        )

        ##################################################
        # Critic Routing
        ##################################################

        workflow.add_conditional_edges(
            "query_critic",
            self._critic_router,
            {
                "investigate": "investigation",
                "revise": "generate_sql",
                "continue": "condition_route",
            },
        )

        ##################################################
        # Condition Route Node
        ##################################################

        workflow.add_node(
            "condition_route",
            lambda state: {"current_node": "condition_route"},
        )

        ##################################################
        # Investigation Loop
        ##################################################

        workflow.add_edge(
            "investigation",
            "generate_sql",
        )

        ##################################################
        # Final Query Routing
        ##################################################

        workflow.add_conditional_edges(
            "condition_route",
            self.condition_router,
            {
                "execute": "execute_query",
                "demo": "demo_application",
            },
        )

        ##################################################
        # Execution → Response
        ##################################################

        workflow.add_edge(
            "execute_query",
            "response",
        )

        ##################################################
        # Demo Approval
        ##################################################

        workflow.add_conditional_edges(
            "demo_application",
            self._demo_router,
            {
                "execute": "execute_query",
                "end": END,
            },
        )

        ##################################################
        # Response → End
        ##################################################

        workflow.add_edge(
            "response",
            END,
        )

        ##################################################
        # Compile
        ##################################################

        return workflow.compile(checkpointer=checkpointer)
