from pydantic import BaseModel, Field
from typing import Literal

DatabaseType = Literal["mysql", "postgresql", "mongodb"]


class DatabaseConfig(BaseModel):
    database_type: DatabaseType

    host: str
    port: int

    username: str | None = None
    password: str | None = None

    database: str


class ConnectionResponse(BaseModel):
    success: bool
    message: str
