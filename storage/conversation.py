from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Conversation:

    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    title: str = "New Chat"

    thread_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    created_at: datetime = field(
        default_factory=datetime.now
    )