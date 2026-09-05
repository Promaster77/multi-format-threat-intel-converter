"""Settings via pydantic-settings BaseSettings (env-driven)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MINIMAX_API_KEY: str = ""
    MINIMAX_API_URL: str = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    MINIMAX_MODEL: str = "MiniMax-Text-01"
    DATABASE_URL: str = "sqlite:///./sih_demo.db"
    MAX_RETRIES: int = 2
    REQUEST_TIMEOUT: int = 60
    LOG_LEVEL: str = "INFO"


settings = Settings()