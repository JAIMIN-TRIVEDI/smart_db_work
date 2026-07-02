from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from db_models.database import DatabaseConfig
from storage.conversation import Conversation


@dataclass
class Project:

    id: str

    title: str

    connection_name: str

    database_config: DatabaseConfig

    connector: Any = None

    conversations: list[Conversation] = field(default_factory=list)

    active_conversation: str | None = None

    created_at: datetime = field(default_factory=datetime.now)

    #######################################################

    def create_conversation(self, title="New Chat"):

        conversation = Conversation(title=title)

        self.conversations.append(conversation)

        self.active_conversation = conversation.id

        return conversation

    #######################################################

    def get_active_conversation(self):

        if self.active_conversation is None:

            return None

        for conversation in self.conversations:

            if conversation.id == self.active_conversation:

                return conversation

        return None

    #######################################################

    def switch_conversation(self, conversation_id):

        self.active_conversation = conversation_id

