from State.DBState import AgentState


class IntentRouter:

    DATABASE_INTENTS = {
        "SELECT",
        "SHOW",
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "CREATE",
        "DROP",
        "TRUNCATE",
        "ANALYTICS",
    }

    def __call__(self, state: AgentState):

        if state.identified_intent in self.DATABASE_INTENTS:

            return "schema_fetch"

        return "non_db_query"
