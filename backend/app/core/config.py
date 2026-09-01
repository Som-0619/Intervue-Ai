import os
import re
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'intervue_ai.db')}"
    
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    KNOWLEDGE_BASE_DIR: str = os.path.join(BASE_DIR, "knowledge-base")
    VECTOR_STORE_PATH: str = os.path.join(BASE_DIR, "vector_store.json")
    
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_sanitized_summary(self) -> dict:
        return {
            "ENVIRONMENT": self.ENVIRONMENT,
            "LLM_PROVIDER": self.LLM_PROVIDER,
            "GEMINI_API_KEY": "***" if self.GEMINI_API_KEY else "Not Set",
            "OPENAI_API_KEY": "***" if self.OPENAI_API_KEY else "Not Set",
            "DATABASE_URL": self.DATABASE_URL
        }

def sanitize_secret_text(text: str) -> str:
    """Redact potential API keys or token strings from log messages or exception details."""
    if not text:
        return ""
    # Mask key patterns
    text = re.sub(r'AIzaSy[A-Za-z0-9_\-]{33}', 'AIzaSy***REDACTED***', text)
    text = re.sub(r'sk-[A-Za-z0-9_\-]{32,}', 'sk-***REDACTED***', text)
    return text

settings = Settings()
