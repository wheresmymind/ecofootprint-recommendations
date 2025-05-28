# app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings # Asegúrate que usas pydantic_settings
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "DEFAULT_KEY_IF_NOT_SET")
    AWS_RDS_URL: Optional[str] = os.getenv("AWS_RDS_URL") # Nueva variable

    # Para construir la DSN de psycopg a partir de los componentes de la URL
    # Esto es útil si prefieres definir las partes de la URL por separado en .env
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    DB_PORT: Optional[int] = os.getenv("DB_PORT", 5432)
    DB_SSLMODE: Optional[str] = os.getenv("DB_SSLMODE", "require")


    class Config:
        env_file = ".env"
        case_sensitive = True
        # extra = 'ignore' # Si quieres ignorar variables extra en .env

settings = Settings()

# Validar que la configuración de la BD esté presente si se va a usar
if not settings.AWS_RDS_URL and not (settings.DB_HOST and settings.DB_USER and settings.DB_PASSWORD and settings.DB_NAME):
    print("ADVERTENCIA: La configuración de la base de datos (AWS_RDS_URL o DB_HOST/USER/...) no está completa en .env.")