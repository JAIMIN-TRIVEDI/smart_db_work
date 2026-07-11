READ_INTENTS = {
    "SELECT",
    "SHOW",
    "DESCRIBE",
    "DESC",
    "EXPLAIN",
    "ANALYTICS",
    "AGGREGATION",
    "REPORT",
    "SCHEMA_INFO",
    "DATABASE_INFO",
}

READ_PREFIXES = ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "WITH")


def is_read_query(
    intent: str | None = None, query_type: str | None = None, query: str | None = None
) -> bool:
    if (query_type or "").strip().lower() == "read":
        return True
    if (intent or "").strip().upper() in READ_INTENTS:
        return True
    return (query or "").lstrip().upper().startswith(READ_PREFIXES)
