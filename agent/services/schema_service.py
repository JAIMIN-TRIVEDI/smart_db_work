from connectors.manager import connection_manager

from State.DBState import AgentState


class SchemaService:
    """
    Responsible only for retrieving the database schema.

    Currently retrieves the complete schema from the connector.
    Later this will be replaced by Vector DB retrieval without
    changing any node logic.
    """

    def fetch_schema(self, state: AgentState):

        connector = connection_manager.get_connection(
            state.connection_name
        )

        return connector.get_schema()