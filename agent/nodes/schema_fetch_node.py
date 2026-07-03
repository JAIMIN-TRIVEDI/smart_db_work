from State.DBState import AgentState
from agent.services.schema_service import SchemaService


class SchemaFetchNode:

    def __init__(self):
        self.schema_service = SchemaService()

    def __call__(self, state: AgentState):

        print("=" * 80)
        print("Entered SchemaFetchNode")

        schema = self.schema_service.fetch_schema(state)

        print("Schema fetched:")
        print(schema)

        print("=" * 80)

        return {
            "schema_context": schema,
            "current_node": "schema_fetch",
        }