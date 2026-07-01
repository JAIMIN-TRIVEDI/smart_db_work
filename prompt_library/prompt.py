from enum import Enum
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate


class IntentType(str, Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ANALYTICS = "ANALYTICS"
    AGGREGATION = "AGGREGATION"
    REPORT = "REPORT"
    SCHEMA_INFO = "SCHEMA_INFO"
    DATABASE_INFO = "DATABASE_INFO"
    UNKNOWN = "UNKNOWN"


class IntentDetectionOutput(BaseModel):
    identified_intent: IntentType = Field(
        ...,
        description="The detected user intent."
    )


INTENT_DETECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Database Intent Classification Agent.

Your ONLY responsibility is to identify the user's intent.

Do NOT:
- Generate SQL
- Explain SQL
- Guess database schema
- Ask questions

Supported intents:

- SELECT
- INSERT
- UPDATE
- DELETE
- ANALYTICS
- AGGREGATION
- REPORT
- SCHEMA_INFO
- DATABASE_INFO
- UNKNOWN

Classify the user query into exactly one intent.
Return your answer using the required structured output schema.
"""
        ),
        (
            "human",
            """
User Query:

{user_query}
"""
        ),
    ]
)