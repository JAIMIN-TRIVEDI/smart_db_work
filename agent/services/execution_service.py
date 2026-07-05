from __future__ import annotations

from connectors.manager import connection_manager
from db_models.database import DatabaseConfig
from exception.exceptions import DatabaseNotConnectedError

from State.DBState import AgentState


class ExecutionService:

    def _get_connector(
        self,
        state: AgentState,
    ):
        try:
            return connection_manager.get_connection(state.connection_name)

        except DatabaseNotConnectedError:

            if not state.connection_name or not state.database_config:
                raise

            return connection_manager.connect(
                state.connection_name,
                DatabaseConfig(**state.database_config),
            )

    def execute(
        self,
        state: AgentState,
    ):
        connector = self._get_connector(state)

        query = state.generated_sql_query

        if not query:
            raise ValueError("No generated query available " "for execution.")

        print("=" * 80)
        print("EXECUTION SERVICE")
        print(
            "Connector:",
            type(connector).__name__,
        )
        print(
            "Query:",
            query,
        )

        if not hasattr(
            connector,
            "execute_query",
        ):
            raise AttributeError(
                f"{type(connector).__name__} " "does not implement execute_query()."
            )

        result = connector.execute_query(query)

        print(
            "Execution result type:",
            type(result).__name__,
        )

        print("Execution completed.")

        return result
