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
    
    def execute_query(self, query: str):

        if self.engine is None:
            raise DatabaseConnectionError("Database not connected.")

        with self.engine.connect() as conn:

            result = conn.execute(text(query))

            try:
                return [dict(row._mapping) for row in result]
            except Exception:
                conn.commit()
                return {
                    "success": True,
                    "rows_affected": result.rowcount,
                }
