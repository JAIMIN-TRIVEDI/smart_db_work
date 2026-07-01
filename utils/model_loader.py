import os
from dotenv import load_dotenv
from typing import Literal, Optional, Any
import dotenv
from pydantic import BaseModel, Field
from utils.config_loader import load_config
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

class ConfigLoader:
    def __init__(self):
        print(f"Loaded config.....")
        self.config = load_config()
    
    def __getitem__(self, key):
        return self.config[key]

class ModelLoader(BaseModel):
    model_provider: Literal["groq", "openai"] = "groq"
    config: Optional[ConfigLoader] = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        self.config = ConfigLoader()
    
    class Config:
        arbitrary_types_allowed = True
    
    def load_llm(self):

        print("========== CONFIG ==========")
        print(self.config.config)

        print("========== GROQ ==========")
        print(self.config["llm"]["groq"])

        model = self.config["llm"]["groq"]["model"]

        print("MODEL =", model)

        api_key = os.getenv("GROQ_API_KEY")

        print("API KEY FOUND =", api_key is not None)

        llm = ChatGroq(
            model=model,
            api_key=api_key,
        )

        return llm
    