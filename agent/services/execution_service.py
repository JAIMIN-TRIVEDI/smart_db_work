from connectors.manager import connection_manager

from State.DBState import AgentState


class ExecutionService:

    def execute(self, state: AgentState):

        connector = connection_manager.get_connection(
            state.connection_name
        )

        return connector.execute_query(
            state.generated_sql_query
        )