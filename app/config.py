from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    openai_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str

    # Agent behaviour — override in .env if you like
    openai_model: str = "gpt-4o-realtime-preview-2024-10-01"
    voice: str = "alloy"
    system_prompt: str = (
        "You are a friendly and helpful voice assistant. "
        "Keep responses concise and conversational — this is a phone call. "
        "Avoid long lists or markdown; just speak naturally."
    )

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
