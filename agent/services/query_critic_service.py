from __future__ import annotations

import json
from typing import Literal, Optional

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from State.DBState import AgentState
from utils.model_loader import ModelLoader


class QueryCriticOutput(BaseModel):

    decision: Literal[
        "ACCEPT",
        "REVISE",
        "INVESTIGATE",
    ] = Field(
        ...,
        description=(
            "ACCEPT when query is correct and grounded. "
            "REVISE when current context is enough to fix it. "
            "INVESTIGATE when database values must be read first."
        ),
    )

    reasoning: str = Field(
        ...,
        description="Reason for the critic decision.",
    )

    investigation_query: Optional[str] = Field(
        default=None,
        description=(
            "One safe read-only investigation query. "
            "Must match the connected database type."
        ),
    )


class QueryCriticService:

    def __init__(
        self,
        model_provider: str = "groq",
    ):
        self.llm = ModelLoader(model_provider=model_provider).load_llm()

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are a strict database query critic.

You receive:
- original user request
- detected intent
- connected database type
- retrieved schema
- generated query
- prior investigation evidence

Your job is to decide exactly one:

ACCEPT
REVISE
INVESTIGATE


==================================================
CRITICAL DATABASE TYPE RULE
==================================================

The connected database type is explicitly provided.

You MUST obey it.

If DATABASE TYPE is mongodb:

- Never generate SQL.
- Never query information_schema.
- Never generate SELECT.
- Never generate SHOW TABLES.
- Never generate DESCRIBE.
- Investigation must use MongoDB read syntax only.

Allowed MongoDB investigation patterns:

db.collection.find({{}})
db.collection.findOne({{}})
db.collection.countDocuments({{}})
db.collection.distinct("field")

If DATABASE TYPE is SQL:

- Never generate MongoDB shell syntax.
- Investigation must be safe read-only SQL.


==================================================
ACCEPT RULES
==================================================

Choose ACCEPT when:

1. The generated query satisfies the user request.
2. Referenced tables/collections exist in schema.
3. Referenced columns/fields exist in schema.
4. No user constraint was silently ignored.
5. No unknown database value must be discovered first.

Examples:

User:
show me first 3 records

Mongo query:
db.sales.find({{}}).limit(3)

Decision:
ACCEPT

Reason:
No unknown stored value must be discovered.


User:
show first 3 records sorted by id

Schema contains _id.

Mongo query:
db.sales.find({{}}).sort({{ "_id": 1 }}).limit(3)

Decision:
ACCEPT


==================================================
REVISE RULES
==================================================

Choose REVISE when:

- The query has the wrong limit.
- The query uses the wrong known field.
- The query ignores an explicit constraint.
- The query syntax can be corrected using current schema.
- No database investigation is required.

Example:

User:
show first 3 records

Generated query:
db.sales.find({{}}).limit(10)

Decision:
REVISE


==================================================
INVESTIGATE RULES
==================================================

Choose INVESTIGATE only when actual database values
must be read before a reliable final query can be made.

Examples:

User:
show sales in denver

Schema proves:
storeLocation is a string

Generated:
db.sales.find({{ "storeLocation": "denver" }})

Exact stored capitalization is unknown.

Decision:
INVESTIGATE

Mongo investigation:
db.sales.distinct("storeLocation")


User:
show employees in marketing

SQL schema proves:
department exists

Exact stored department value is unknown.

Decision:
INVESTIGATE

SQL investigation:
SELECT DISTINCT department FROM employees;


==================================================
IMPORTANT
==================================================

Do NOT investigate merely because you want more schema.

The schema is already provided.

Do NOT claim the user request is missing when USER REQUEST
contains text.

Do NOT claim the generated query is missing when GENERATED
QUERY contains text.

Do NOT use information_schema for MongoDB.

For simple limit queries such as:
- first 3 records
- show 10 rows
- give me 5 documents

normally ACCEPT when the generated query has the correct limit.

Return only structured output.
""",
                ),
                (
                    "human",
                    """
USER REQUEST:
{user_query}

DETECTED INTENT:
{intent}

DATABASE TYPE:
{database_type}

RETRIEVED SCHEMA:
{schema_info}

GENERATED QUERY:
{generated_query}

PRIOR INVESTIGATION EVIDENCE:
{evidence}

REFINEMENT COUNT:
{refinement_count}
""",
                ),
            ]
        )

    def review(
        self,
        state: AgentState,
    ) -> QueryCriticOutput:

        schema_context = state.schema_context or {}

        if isinstance(
            schema_context,
            dict,
        ):
            schema_info = schema_context.get("schema_markdown") or json.dumps(
                schema_context,
                default=str,
            )
        else:
            schema_info = str(schema_context)

        database_config = state.database_config or {}

        database_type = str(
            database_config.get(
                "database_type",
                "",
            )
        ).lower()

        user_query = state.user_input or ""

        generated_query = state.generated_sql_query or ""

        evidence = state.investigation_evidence or "None"

        print("=" * 80)
        print("QUERY CRITIC SERVICE INPUT")
        print("User query:", user_query)
        print("Intent:", state.identified_intent)
        print("Database type:", database_type)
        print("Generated query:", generated_query)
        print("Evidence:", evidence)
        print("Refinement count:", state.refinement_count)
        print("=" * 80)

        structured_llm = self.llm.with_structured_output(QueryCriticOutput)

        chain = self.prompt | structured_llm

        result = chain.invoke(
            {
                "user_query": user_query,
                "intent": state.identified_intent or "",
                "database_type": database_type,
                "schema_info": schema_info,
                "generated_query": generated_query,
                "evidence": evidence,
                "refinement_count": state.refinement_count,
            }
        )

        print("=" * 80)
        print("QUERY CRITIC SERVICE OUTPUT")
        print("Decision:", result.decision)
        print("Reasoning:", result.reasoning)
        print(
            "Investigation query:",
            result.investigation_query,
        )
        print("=" * 80)

        return result
