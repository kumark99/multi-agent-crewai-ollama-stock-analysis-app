import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    default_llm_model: str = "llama3.2"
    reports_dir: str = "reports"
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()
