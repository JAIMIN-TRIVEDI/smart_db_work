from State.DBState import AgentState

from agent.services.sql_generation_service import (
    SQLGenerationService,
)


class SQLGenerationNode:

    def __init__(self):
        self.sql_service = SQLGenerationService()

    def __call__(self, state: AgentState):
        plan = self.sql_service.generate_sql(state)

        print("=" * 80)
        print("Generated Query:")
        print(plan.generated_query)
        print("=" * 80)

        return {
            "generated_sql_query": plan.generated_query,
            "query_confidence": plan.confidence,
            "query_risk_level": plan.risk_level,
            "requires_approval": plan.requires_approval,
            "query_reasoning": plan.reasoning,
            "query_type": plan.query_type,
            "affected_tables": plan.affected_tables,
            "critic_status": None,
            "current_node": "generate_sql",
        }
