from utils.model_loader import ModelLoader
from prompt_library.prompt import (
    INTENT_DETECTION_PROMPT,
    IntentDetectionOutput,
)

from langgraph.graph import StateGraph, START, END
from State.DBState import AgentState


class GraphBuilder:

    def __init__(self, model_provider: str = "groq"):

        self.model_loader = ModelLoader(
            model_provider=model_provider
        )

        self.llm = self.model_loader.load_llm()

        self.graph = None

    def intent_detection_node(self, state: AgentState):

        structured_llm = self.llm.with_structured_output(
            IntentDetectionOutput
        )

        chain = (
            INTENT_DETECTION_PROMPT
            | structured_llm
        )

        result = chain.invoke(
            {
                "user_query": state.user_query
            }
        )

        print(
            f"Identified Intent: {result.identified_intent.value}"
        )

        # Return only updated fields
        return {
            "identified_intent": result.identified_intent.value
        }

    def build_graph(self):

        workflow = StateGraph(AgentState)

        workflow.add_node(
            "intent_detection",
            self.intent_detection_node,
        )

        workflow.add_edge(
            START,
            "intent_detection",
        )

        workflow.add_edge(
            "intent_detection",
            END,
        )

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