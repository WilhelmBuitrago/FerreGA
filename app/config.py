import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto (un nivel arriba de app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ferrega.db")
print(f"[CONFIG] DATABASE_URL loaded: {DATABASE_URL}", flush=True)
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 semana

# AI Parser configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
AI_PARSER_ENABLED = os.getenv("AI_PARSER_ENABLED", "true").lower() == "true"
AI_PARSER_MODE = os.getenv("AI_PARSER_MODE", "legacy")  # "legacy" o "auto"

# NVIDIA provider configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "stepfun-ai/step-3.7-flash")
AI_PARSER_PROVIDER = os.getenv("AI_PARSER_PROVIDER", "nvidia")  # "nvidia" o "groq"
