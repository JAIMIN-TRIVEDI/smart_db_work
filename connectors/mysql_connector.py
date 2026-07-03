from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from db_models.database import DatabaseConfig
from exception.exceptions import (
    DatabaseConnectionError,
    AuthenticationError,
)


class MySQLConnector:
    """
    Handles MySQL database connection using SQLAlchemy.
    """

    def __init__(self):
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker | None = None
        self.config: DatabaseConfig | None = None

    @property
    def is_connected(self) -> bool:
        return self.engine is not None

    def connect(self, config: DatabaseConfig) -> bool:
        """
        Create SQLAlchemy Engine.
        """

        try:

            url = (
                f"mysql+pymysql://"
                f"{config.username}:{config.password}"
                f"@{config.host}:{config.port}"
                f"/{config.database}"
            )

            self.engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                future=True,
            )

            self.engine.connect().close()

            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False,
                future=True,
            )

            self.config = config

            return True

        except SQLAlchemyError as e:

            msg = str(e).lower()

            if "access denied" in msg:
                raise AuthenticationError(str(e))

            raise DatabaseConnectionError(str(e))

    def disconnect(self):

        if self.engine:
            self.engine.dispose()

        self.engine = None
        self.SessionLocal = None
        self.config = None

    def test(self) -> bool:

        if not self.engine:
            return False

        try:

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return True

        except Exception:
            return False

    def get_engine(self) -> Engine:

        if self.engine is None:
            raise DatabaseConnectionError("Database not connected.")

        return self.engine

    def get_session(self) -> Session:

        if self.SessionLocal is None:
            raise DatabaseConnectionError("Database not connected.")

        return self.SessionLocal()
    
    def execute_query(self, query: str) -> dict:

        if self.engine is None:
            raise DatabaseConnectionError("Database not connected.")

        with self.engine.connect() as conn:

            result = conn.execute(text(query))

            try:
                rows = [dict(row._mapping) for row in result]

                return {
                    "success": True,
                    "query_type": "SELECT",
                    "rows": rows
                }
            
            except Exception:
                conn.commit()
                return {
                    "success": True,
                    "query_type":"MODIFICATION",
                    "rows_affected": result.rowcount,
                    "rows": []
                }

    def get_schema(self) -> dict:

        """
        Returns complete database schema.

        {
            "table1": {
                "columns": [
                    {
                        "name": "...",
                        "type": "...",
                        "nullable": True,
                        "key": "PRI"
                    }
                ]
            }
        }
        """

        if self.engine is None:
            raise DatabaseConnectionError("Database not connected.")

        schema = {}

        with self.engine.connect() as conn:

            tables = conn.execute(
                text(
                    """
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE();
                    """
                )
            )

            table_names = [row[0] for row in tables]

            for table in table_names:

                columns = conn.execute(
                    text(
                        """
                        SELECT
                            COLUMN_NAME,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_KEY
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = :table;
                        """
                    ),
                    {
                        "table": table
                    }
                )

                schema[table] = {
                    "columns": [
                        {
                            "name": row.COLUMN_NAME,
                            "type": row.DATA_TYPE,
                            "nullable": row.IS_NULLABLE == "YES",
                            "key": row.COLUMN_KEY,
                        }
                        for row in columns
                    ]
                }

        return schema