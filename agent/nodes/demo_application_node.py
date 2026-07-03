from langgraph.types import interrupt

from State.DBState import AgentState


class DemoApplicationNode:

    def __call__(self, state: AgentState):

        approval = interrupt(
            {
                "type": "demo_approval",
                "sql": state.generated_sql_query,
                "intent": state.identified_intent,
                "message": (
                    "This query modifies the database.\n"
                    "Demo preview will be shown here.\n"
                    "Do you want to continue?"
                ),
            }
        )

        return {

            "workflow_status": "approved"
            if approval
            else "cancelled",

            "current_node": "demo_application",

            "approval": approval

        }