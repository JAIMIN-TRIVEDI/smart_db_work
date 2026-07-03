from langchain_core.messages import HumanMessage

from State.DBState import AgentState

from agent.services.intent_service import IntentService


class UserQueryNode:

    def __init__(self):

        self.intent_service = IntentService()

    def __call__(self, state: AgentState):

        if not state.messages:

            raise ValueError("No conversation messages found.")

        last_message = state.messages[-1]

        if not isinstance(last_message, HumanMessage):

            raise ValueError("Last message must be a HumanMessage.")

        user_input = last_message.content
        
        if not user_input:

            raise ValueError("No user input found.")

        intent = self.intent_service.detect_intent(
            user_input
        )

        print(f"Detected Intent : {intent}")

        return {

            "user_input": user_input,

            "identified_intent": intent,

            "current_node": "user_query"
        }