from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from State.DBState import AgentState
from connectors.manager import connection_manager
from connectors.mysql_connector import MySQLConnector
from db_models.database import DatabaseConfig
from exception.exceptions import DatabaseNotConnectedError


class DemoDatabaseService:
    """Execute a write preview in a disposable MySQL database."""

    SNAPSHOT_LIMIT = 100

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        if not identifier or "\x00" in identifier:
            raise ValueError("A valid database or table name is required for preview.")
        return f"`{identifier.replace('`', '``')}`"

    def _get_connector(self, state: AgentState):
        try:
            return connection_manager.get_connection(state.connection_name)
        except DatabaseNotConnectedError:
            if not state.connection_name or not state.database_config:
                raise
            return connection_manager.connect(
                state.connection_name, DatabaseConfig(**state.database_config)
            )

    def _snapshot(self, engine: Engine, table_name: str) -> list[dict]:
        with engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT * FROM {self._quote_identifier(table_name)} LIMIT :limit"),
                {"limit": self.SNAPSHOT_LIMIT},
            )
            return [dict(row._mapping) for row in rows]

    def _clone_table(self, source_engine: Engine, sandbox_connection, sandbox_name: str, table_name: str):
        source_database = source_engine.url.database
        if not source_database:
            raise ValueError("The connected MySQL database name is unavailable.")
        source_table = (
            f"{self._quote_identifier(source_database)}."
            f"{self._quote_identifier(table_name)}"
        )
        sandbox_table = (
            f"{self._quote_identifier(sandbox_name)}."
            f"{self._quote_identifier(table_name)}"
        )
        with source_engine.connect() as connection:
            create_statement = connection.execute(
                text(f"SHOW CREATE TABLE {source_table}")
            ).one()._mapping["Create Table"]
            sandbox_connection.execute(text(create_statement))
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            try:
                connection.execute(
                    text(f"INSERT INTO {sandbox_table} SELECT * FROM {source_table}")
                )
                connection.commit()
            finally:
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                connection.commit()

    @staticmethod
    def _assert_query_is_sandbox_scoped(sql: str, source_database: str):
        normalized = sql.casefold()
        source = source_database.casefold()
        if f"{source}." in normalized or f"`{source}`." in normalized:
            raise ValueError(
                "The preview query explicitly references the real database; "
                "use unqualified table names so it can run in the sandbox."
            )

    def preview(self, state: AgentState, affected_tables: list[str]) -> dict:
        if not affected_tables:
            raise ValueError("No affected tables were supplied for a safe sandbox preview.")
        if not state.generated_sql_query:
            raise ValueError("No generated SQL query is available for preview.")

        connector = self._get_connector(state)
        if not isinstance(connector, MySQLConnector):
            raise NotImplementedError("Sandbox previews currently require a MySQL connection.")

        source_engine = connector.get_engine()
        source_database = source_engine.url.database
        if not source_database:
            raise ValueError("The connected MySQL database name is unavailable.")
        self._assert_query_is_sandbox_scoped(state.generated_sql_query, source_database)

        sandbox_name = f"smart_db_preview_{uuid4().hex}"
        sandbox_identifier = self._quote_identifier(sandbox_name)
        sandbox_engine: Engine | None = None

        try:
            with source_engine.connect() as connection:
                connection.execute(text(f"CREATE DATABASE {sandbox_identifier}"))
                connection.commit()

            sandbox_engine = create_engine(
                source_engine.url.set(database=sandbox_name), pool_pre_ping=True, future=True
            )
            with sandbox_engine.connect() as connection:
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                for table_name in affected_tables:
                    self._clone_table(source_engine, connection, sandbox_name, table_name)
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                connection.commit()

            before_snapshots = {
                table_name: self._snapshot(sandbox_engine, table_name)
                for table_name in affected_tables
            }
            with sandbox_engine.connect() as connection:
                connection.execute(text(state.generated_sql_query))
                connection.commit()
            after_snapshots = {
                table_name: self._snapshot(sandbox_engine, table_name)
                for table_name in affected_tables
            }
            primary_table = affected_tables[0]
            return {
                "table_name": primary_table,
                "affected_tables": affected_tables,
                "before": before_snapshots[primary_table],
                "after": after_snapshots[primary_table],
                "table_snapshots": {
                    table_name: {"before": before_snapshots[table_name], "after": after_snapshots[table_name]}
                    for table_name in affected_tables
                },
                "caution": "Sandbox preview only. The generated query was executed against a temporary database, not the real database.",
                "summary": f"Preview executed in an isolated sandbox for: {', '.join(affected_tables)}. Snapshots show up to {self.SNAPSHOT_LIMIT} rows per table.",
                "sql": state.generated_sql_query,
                "risk_level": state.query_risk_level,
                "confidence": state.query_confidence,
            }
        finally:
            if sandbox_engine is not None:
                sandbox_engine.dispose()
            with source_engine.connect() as connection:
                connection.execute(text(f"DROP DATABASE IF EXISTS {sandbox_identifier}"))
                connection.commit()




