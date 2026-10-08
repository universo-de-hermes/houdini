"""
Houdini - Configuración central
Carga variables de entorno y expone settings tipados.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # === General ===
    app_name: str = "Houdini"
    environment: str = "local"  # local | vps
    debug: bool = True
    log_level: str = "INFO"

    # === OpenRouter (LLM) ===
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-v4-pro"

    # Modelo principal y fallback
    primary_model: str = "deepseek/deepseek-v4-pro"
    fallback_model: str = "openai/gpt-4o"

    # === Anthropic (Claude) ===
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # === PostgreSQL + pgvector ===
    postgres_user: str = "houdini"
    postgres_password: str = "houdini_secret"
    postgres_db: str = "houdini_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # === Telegram ===
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    # === Google OAuth ===
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = "http://localhost:8000/oauth/callback"
    google_credentials_file: str = "config/google_token.json"

    # === WhatsApp (fase 2) ===
    whatsapp_enabled: bool = False

    # === TTS (Salome voice) ===
    tts_enabled: bool = True
    tts_voice: str = "es-CO-SalomeNeural"
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"

    # === Embeddings ===
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reload_settings():
    """Limpia la caché para recargar settings desde el .env."""
    get_settings.cache_clear()
    return get_settings()