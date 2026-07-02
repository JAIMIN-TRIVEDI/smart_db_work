from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from db_models.database import DatabaseConfig


@dataclass
class Project:

    id: str

    title: str

    connection_name: str

    database_config: DatabaseConfig

    chat_history: list = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)

    connector: Any = None

    def add_message(self, role, content):

        self.chat_history.append({"role": role, "content": content})
