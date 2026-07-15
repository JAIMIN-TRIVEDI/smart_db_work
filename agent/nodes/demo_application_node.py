from State.DBState import AgentState
from agent.services.demo_database_service import DemoDatabaseService
from utils.query_types import is_read_query


class DemoApplicationNode:
    """Build an isolated, database-backed preview for modification queries."""

    def __init__(self):
        self.demo_database_service = DemoDatabaseService()

    def __call__(self, state: AgentState):
        if is_read_query(
            state.identified_intent, state.query_type, state.generated_sql_query
        ):
            return {"current_node": "demo_application", "demo_result": None}

        tables = list(dict.fromkeys(state.affected_tables or []))
        try:
            demo_result = self.demo_database_service.preview(state, tables)
        except Exception as exc:
            demo_result = {
                "table_name": tables[0] if tables else None,
                "affected_tables": tables,
                "before": [],
                "after": [],
                "caution": "Sandbox preview could not be created. The real database was not modified during preview.",
                "summary": str(exc),
                "sql": state.generated_sql_query,
                "risk_level": state.query_risk_level,
                "confidence": state.query_confidence,
            }

        return {
            "workflow_status": "pending_approval",
            "current_node": "demo_application",
            "approval": False,
            "demo_result": demo_result,
        }
