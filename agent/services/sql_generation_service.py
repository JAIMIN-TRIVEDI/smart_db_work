from utils.model_loader import ModelLoader

from prompt_library.prompt import (
    QUERY_GENERATION_PROMPT,
    QueryGenerationOutput,
)

from State.DBState import AgentState


class SQLGenerationService:

    def __init__(self, model_provider: str = "groq"):

        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()

    def generate_sql(self, state: AgentState) -> str:

        structured_llm = self.llm.with_structured_output(
            QueryGenerationOutput
        )

        chain = QUERY_GENERATION_PROMPT | structured_llm

        result = chain.invoke(
            {
                "user_query": state.user_input,
                "intent": state.identified_intent,
                "schema_info": state.schema_context,
            }
        )

        return result.generated_query