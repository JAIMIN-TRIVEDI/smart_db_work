from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from State.DBState import AgentState
from utils.query_types import is_read_query


class FinalizeQueryNode:
    """Persist one immutable UI snapshot for the completed database turn."""

    def __call__(self, state: AgentState):
        if not state.user_input or not state.generated_sql_query:
            return {"current_node": "finalize_query"}

        turn = {
            "id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_input": state.user_input,
            "identified_intent": state.identified_intent,
            "generated_sql_query": state.generated_sql_query,
            "query_confidence": state.query_confidence,
            "query_risk_level": state.query_risk_level,
            "requires_approval": state.requires_approval,
            "query_reasoning": state.query_reasoning,
            "query_type": state.query_type,
            "affected_tables": list(state.affected_tables or []),
            "execution_result": state.execution_result,
            "demo_result": state.demo_result,
            "workflow_status": state.workflow_status,
            "is_read": is_read_query(
                state.identified_intent,
                state.query_type,
                state.generated_sql_query,
            ),
        }

        return {
            "query_history": [*(state.query_history or []), turn],
            "current_node": "finalize_query",
        }
