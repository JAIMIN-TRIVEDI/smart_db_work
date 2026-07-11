from __future__ import annotations

from State.DBState import AgentState
from agent.services.execution_service import ExecutionService
from utils.query_types import is_read_query


class ExecuteQueryNode:
    def __init__(self):
        self.execution_service = ExecutionService()

    def __call__(self, state: AgentState):
        print("=" * 80)
        print("ENTERED EXECUTE QUERY NODE")
        print("Intent:", state.identified_intent)
        print("Query:", state.generated_sql_query)

        if (
            not is_read_query(
                state.identified_intent,
                state.query_type,
                state.generated_sql_query,
            )
            and state.approval is not True
        ):
            raise PermissionError("Modification query executed without approval.")

        result = self.execution_service.execute(state)
        return {
            "execution_result": result,
            "workflow_status": "executed",
            "current_node": "execute_query",
        }
