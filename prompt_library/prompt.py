from enum import Enum

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate


########################################################
# Intent Detection
########################################################

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
        description="Detected user intent."
    )


INTENT_DETECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Database Intent Classification Agent.

Your ONLY responsibility is to classify the user's database intent.

Do NOT:
- Generate SQL
- Explain SQL
- Ask questions
- Guess schema

Supported intents:

SELECT
INSERT
UPDATE
DELETE
ANALYTICS
AGGREGATION
REPORT
SCHEMA_INFO
DATABASE_INFO
UNKNOWN

Return ONLY the structured output.
""",
        ),
        (
            "human",
            """
User Query:
{user_query}
""",
        ),
    ]
)

########################################################
# SQL Generation
########################################################


class QueryGenerationOutput(BaseModel):

    generated_query: str = Field(
        ...,
        description="Generated SQL query."
    )


QUERY_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert SQL Generation Agent.

Generate a valid SQL query.

Rules:

- Use ONLY the provided schema.
- Never invent table names.
- Never invent column names.
- Never explain anything.
- Return ONLY the SQL query using the structured output.
""",
        ),
        (
            "human",
            """
            User Query:
            {user_query}

            Intent:
            {intent}

            Database Schema:
            {schema_info}
            """,
        ),
    ]
)