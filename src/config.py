import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Project JARVIS."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Google Gemini API
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Security & Voice Passcode Authorization
    JARVIS_SECRET_CODE: str = "omega-protocol-9"
    SESSION_TIMEOUT_MINUTES: int = 10

    # Voice Engine (Edge-TTS)
    TTS_VOICE: str = "en-GB-RyanNeural"  # Authentic British JARVIS tone
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"

    # Mail Automation (Dedicated Agent Account)
    EMAIL_USER: str = "sanesrujan84@gmail.com"
    EMAIL_APP_PASSWORD: str = ""
    EMAIL_IMAP_SERVER: str = "imap.gmail.com"
    EMAIL_IMAP_PORT: int = 993
    EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 587

    # Database & Memory
    DATABASE_URL: str = "sqlite+aiosqlite:///./jarvis.db"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"

    # Server & Networking
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for cached settings."""
    return Settings()
