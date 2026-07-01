from utils.model_loader import ModelLoader
from prompt_library.prompt import (
    INTENT_DETECTION_PROMPT,
    IntentDetectionOutput,
    QUERY_GENERATION_PROMPT,
    QueryGenerationOutput,
)

from langgraph.graph import StateGraph, START, END
from State.DBState import AgentState


class GraphBuilder:

    def __init__(self, model_provider: str = "groq"):

        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()
        self.graph = None

    def intent_detection_node(self, state: AgentState):
        structured_llm = self.llm.with_structured_output(IntentDetectionOutput)
        chain = INTENT_DETECTION_PROMPT | structured_llm
        result = chain.invoke({"user_query": state.user_query})

        print(f"Identified Intent: {result.identified_intent.value}")

        # Return only updated fields
        return {"identified_intent": result.identified_intent.value}

    def query_generation_node(self, state: AgentState):
        structured_llm = self.llm.with_structured_output(QueryGenerationOutput)
        chain = QUERY_GENERATION_PROMPT | structured_llm
        result = chain.invoke(
            {
                "user_query": state.user_query,
                "intent": state.identified_intent,
                # "db_schema": state.db_schema or None,
            }
        )

        print(f"Generated Query: {result.generated_query}")

        # Return only updated fields [State]
        return {"sql_query": result.generated_query}

    #  Newly Added Nodes for Intent Based Routing and Query Execution
    # TODO : Complete the node logic

    def intent_based_routing_node(self, state: AgentState):
        if state.identified_intent == "SELECT":
            return {"next_node": "select_query_execution"}
        else:
            # Default routing
            return {"next_node": END}

    def select_query_execution_node(self, state: AgentState):
        # TODO: Implement the logic to execute the SELECT query against the database

        # Placeholder for executing SELECT queries
        # In a real implementation, this would execute the SQL against the database
        print(f"Executing SELECT query: {state.sql_query}")

        return {"execution_result": "Query executed successfully."}

    def build_graph(self):

        workflow = StateGraph(AgentState)

        workflow.add_node("intent_detection", self.intent_detection_node)
        workflow.add_node("query_generation", self.query_generation_node)

        workflow.add_edge(START, "intent_detection")
        workflow.add_edge("intent_detection", "query_generation")
        workflow.add_edge("query_generation", END)

        self.graph = workflow.compile()

        return self.graph

    def invoke(self, state: AgentState):
        if self.graph is None:
            self.build_graph()

        return self.graph.invoke(state)

    def __call__(self):
        if self.graph is None:
            self.build_graph()

        return self.graph
