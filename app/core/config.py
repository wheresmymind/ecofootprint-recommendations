# app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()
class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "DEFAULT_KEY_IF_NOT_SET") # Add default or raise error

    print(os.getenv("GEMINI_API_KEY"))  
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()