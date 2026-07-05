from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

########################################################
# Intent Detection
########################################################


class IntentType(str, Enum):
    SELECT = "SELECT"
    SHOW = "SHOW"
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
        description="Detected user intent.",
    )


INTENT_DETECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Database Intent Classification Agent.

Your ONLY responsibility is to classify the user's
database intent.

Do NOT:
- Generate SQL
- Generate MongoDB queries
- Explain queries
- Ask questions
- Guess schema

Supported intents:

SELECT
SHOW
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
# Query Generation Output
########################################################


class QueryGenerationOutput(BaseModel):

    generated_query: str = Field(
        ...,
        description=("Generated SQL or NoSQL query."),
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=("Confidence score for the " "generated query."),
    )

    risk_level: Literal[
        "low",
        "medium",
        "high",
    ] = Field(
        ...,
        description=("Risk level of executing " "the generated query."),
    )

    requires_approval: bool = Field(
        ...,
        description=("Whether the user must approve " "the query before execution."),
    )

    query_type: Literal[
        "read",
        "write",
        "schema",
        "unknown",
    ] = Field(
        ...,
        description=("High-level generated query category."),
    )

    reasoning: str = Field(
        ...,
        description=(
            "Brief explanation for the generated " "query and routing decision."
        ),
    )

    affected_tables: list[str] = Field(
        default_factory=list,
        description=("Tables or collections affected " "or referenced by the query."),
    )


########################################################
# Query Generation Prompt
########################################################


QUERY_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert SQL and NoSQL Query Generation Agent.

Generate a valid database query using:
- the user's request
- detected intent
- database type
- retrieved schema
- previous generated query
- critic feedback
- investigation evidence

CORE RULES:

1. Use ONLY tables, collections, columns, and fields
   supported by the provided schema.

2. Never invent table names.

3. Never invent collection names.

4. Never invent column names.

5. Never invent field names.

6. Never silently remove a user constraint.

7. Never guess database values when actual row evidence
   is required.

8. If investigation evidence is available, use it when
   improving the query.

9. If critic feedback is available, correct the exact
   problem identified by the critic.

10. Do not repeat a previously rejected query unless the
    evidence proves it is correct.

SQL RULES:

11. For relational databases, generate valid SQL for the
    connected database.

12. For read operations, use SELECT, SHOW, DESCRIBE,
    EXPLAIN, or another supported read-only operation.

13. For modification operations, generate the smallest
    correctly scoped write query possible.

MONGODB RULES:

14. For MongoDB, generate Mongo shell-style queries
    supported by the execution layer.

Supported read patterns include:

db.collection.find({{}})
db.collection.find({{ "field": "value" }})
db.collection.findOne({{ "field": "value" }})
db.collection.countDocuments({{}})
db.collection.countDocuments({{ "field": "value" }})
db.collection.distinct("field")
db.collection.distinct(
    "field",
    {{ "otherField": "value" }}
)

IMPORTANT:
The double braces in these prompt examples represent
literal MongoDB objects.

Do not generate unsupported MongoDB syntax unless the
execution layer supports it.

ROUTING RULES:

15. SELECT, SHOW, ANALYTICS, AGGREGATION, and REPORT
    queries are normally read operations.

16. Read queries should normally set:
    query_type = "read"
    requires_approval = false

17. INSERT, UPDATE, DELETE, and other modification
    operations should set:
    query_type = "write"
    requires_approval = true

18. Risk must reflect the actual impact:
    - low: read-only
    - medium: limited modification
    - high: broad/destructive modification

19. Confidence must reflect schema grounding and evidence.

20. Return ONLY the required structured output.
""",
        ),
        (
            "human",
            """
USER QUERY:
{user_query}

INTENT:
{intent}

DATABASE TYPE:
{database_type}

RELEVANT SCHEMA:
{schema_info}

PREVIOUS QUERY:
{previous_query}

CRITIC FEEDBACK:
{critic_feedback}

INVESTIGATION EVIDENCE:
{evidence}

REFINEMENT ATTEMPT:
{refinement_count}
""",
        ),
    ]
)
