from State.DBState import AgentState

from agent.services.response_service import ResponseService


class ResponseNode:

    def __init__(self):

        self.response_service = ResponseService()

    def __call__(self, state: AgentState):

        response = self.response_service.build_response(
            state
        )

        return {

            "messages": [response],

            "current_node": "response"

        }