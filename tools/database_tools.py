def execute_query(state, query):
    connector = state.db_connection
    return connector.execute_query(query)

def get_schema(state):
    connector = state.db_connection
    return connector.get_schema()