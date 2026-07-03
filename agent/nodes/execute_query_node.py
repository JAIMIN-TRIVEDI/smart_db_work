from State.DBState import AgentState

from agent.services.execution_service import ExecutionService


class ExecuteQueryNode:

    def __init__(self):

        self.execution_service = ExecutionService()

    def __call__(self, state: AgentState):

        if (
            state.identified_intent != "SELECT"
            and state.approval is not True
        ):
            raise PermissionError(
                "Modification query executed without approval."
            )

        result = self.execution_service.execute(state)

        return {

            "execution_result": result,

            "current_node": "execute_query"

        }