from __future__ import annotations

from State.DBState import AgentState

from prompt_library.prompt import (
    QUERY_GENERATION_PROMPT,
    QueryGenerationOutput,
)

from utils.model_loader import ModelLoader


class SQLGenerationService:

    def __init__(
        self,
        model_provider: str = "groq",
    ):
        self.model_loader = ModelLoader(model_provider=model_provider)

        self.llm = self.model_loader.load_llm()

    def generate_sql(
        self,
        state: AgentState,
    ):
        ####################################################
        # SCHEMA CONTEXT
        ####################################################

        schema_context = state.schema_context or {}

        if isinstance(
            schema_context,
            dict,
        ):
            schema_info = schema_context.get("schema_markdown") or str(schema_context)

        else:
            schema_info = str(schema_context)

        ####################################################
        # DATABASE TYPE
        ####################################################

        database_config = state.database_config or {}

        database_type = str(
            database_config.get(
                "database_type",
                "",
            )
        ).lower()

        ####################################################
        # STRUCTURED LLM
        ####################################################

        structured_llm = self.llm.with_structured_output(QueryGenerationOutput)

        ####################################################
        # PROMPT CHAIN
        ####################################################

        chain = QUERY_GENERATION_PROMPT | structured_llm

        ####################################################
        # DEBUG
        ####################################################

        print("=" * 80)
        print("SQL GENERATION SERVICE")

        print(
            "User query:",
            state.user_input,
        )

        print(
            "Intent:",
            state.identified_intent,
        )

        print(
            "Database type:",
            database_type,
        )

        print(
            "Previous query:",
            state.generated_sql_query,
        )

        print(
            "Critic feedback:",
            state.critic_reasoning,
        )

        print(
            "Refinement count:",
            state.refinement_count,
        )

        print(
            "Has investigation evidence:",
            bool(state.investigation_evidence),
        )

        ####################################################
        # GENERATE
        ####################################################

        result = chain.invoke(
            {
                "user_query": state.user_input or "",
                "intent": state.identified_intent or "",
                "database_type": database_type,
                "schema_info": schema_info,
                "previous_query": state.generated_sql_query or "None",
                "critic_feedback": state.critic_reasoning or "None",
                "evidence": state.investigation_evidence or "None",
                "refinement_count": state.refinement_count,
            }
        )

        ####################################################
        # DEBUG RESULT
        ####################################################

        print(
            "Generated query:",
            result.generated_query,
        )

        print(
            "Confidence:",
            result.confidence,
        )

        print(
            "Risk level:",
            result.risk_level,
        )

        print(
            "Requires approval:",
            result.requires_approval,
        )

        print(
            "Query type:",
            result.query_type,
        )

        print("=" * 80)

        return result
