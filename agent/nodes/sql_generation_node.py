from State.DBState import AgentState

from agent.services.sql_generation_service import (
    SQLGenerationService,
)


class SQLGenerationNode:

    def __init__(self):

        self.sql_service = SQLGenerationService()

    def __call__(self, state: AgentState):

        sql = self.sql_service.generate_sql(state)

        print("=" * 80)
        print("Generated SQL:")
        print(sql)
        print("=" * 80)


        return {

            "generated_sql_query": sql,

            "current_node": "generate_sql"

        }