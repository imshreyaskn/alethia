"""
config.py — Central configuration using Pydantic Settings.

HOW IT WORKS:
Pydantic reads environment variables automatically. When you set
SUPABASE_URL=https://... in your .env file, this class picks it up
without you writing any manual os.getenv() calls.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Realive"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:5173"  # Comma-separated for multiple origins

    # --- Supabase (Milestone 1) ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""  # Service role key — bypasses Row Level Security

    # --- GitHub App (Milestone 2) ---
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""        # Full PEM string (newlines as \n)
    GITHUB_WEBHOOK_SECRET: str = ""         # Used to verify webhooks are from GitHub

    # --- Gemini (kept as fallback reference) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Groq (Milestones 4, 6 — free tier, no billing required) ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Best free Groq model for reasoning

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single shared instance — import this everywhere
settings = Settings()
