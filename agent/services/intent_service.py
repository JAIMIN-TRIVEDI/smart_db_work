from utils.model_loader import ModelLoader

from prompt_library.prompt import (
    INTENT_DETECTION_PROMPT,
    IntentDetectionOutput,
)


class IntentService:

    def __init__(self, model_provider: str = "groq"):

        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()

    def detect_intent(self, user_input: str) -> str:

        structured_llm = self.llm.with_structured_output(
            IntentDetectionOutput
        )

        chain = INTENT_DETECTION_PROMPT | structured_llm

        result = chain.invoke(
            {
                "user_query": user_input
            }
        )

        return result.identified_intent.value