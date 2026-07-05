from __future__ import annotations

from State.DBState import AgentState
from agent.services.execution_service import ExecutionService

READ_INTENTS = {
    "SELECT",
    "SHOW",
    "ANALYTICS",
    "AGGREGATION",
    "REPORT",
    "SCHEMA_INFO",
    "DATABASE_INFO",
}


class ExecuteQueryNode:

    def __init__(self):
        self.execution_service = ExecutionService()

    def __call__(self, state: AgentState):
        print("=" * 80)
        print("ENTERED EXECUTE QUERY NODE")
        print("Intent:", state.identified_intent)
        print("Query:", state.generated_sql_query)

        intent = (state.identified_intent or "").upper()

        if intent not in READ_INTENTS and state.approval is not True:
            raise PermissionError("Modification query executed without approval.")

        result = self.execution_service.execute(state)

        print("Execution result type:", type(result).__name__)
        print("Execution result:", result)

        return {
            "execution_result": result,
            "workflow_status": "executed",
            "current_node": "execute_query",
        }
