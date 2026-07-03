from State.DBState import AgentState


class ConditionRouter:

    READ_INTENTS = {
        "SELECT",
        "ANALYTICS",
        "AGGREGATION",
        "REPORT",
        "SCHEMA_INFO",
        "DATABASE_INFO",
    }

    def __call__(self, state: AgentState):

        if state.identified_intent in self.READ_INTENTS:
            return "execute"

        return "demo"