import os
from pathlib import Path
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'acadivance.db').as_posix()}"

class Settings(BaseModel):
    APP_NAME: str = "Acadivance — Smart Campus Analytics"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "acadivance-super-secret-key-2025-token-auth")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    WEB_AUTHN_RP_ID: str = os.getenv("WEB_AUTHN_RP_ID", "localhost")
    WEB_AUTHN_RP_NAME: str = os.getenv("WEB_AUTHN_RP_NAME", "College Portal")
    WEB_AUTHN_ORIGIN: str = os.getenv("WEB_AUTHN_ORIGIN", "http://localhost:8000")

    # Free local LLM configuration using Ollama (https://ollama.com)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Default scoring weights (S = 0.35A + 0.20T + 0.15L + 0.20P + 0.10E)
    WEIGHT_ACADEMIC: float = 0.35
    WEIGHT_ATTENDANCE: float = 0.20
    WEIGHT_LMS: float = 0.15
    WEIGHT_PLACEMENT: float = 0.20
    WEIGHT_ENGAGEMENT: float = 0.10
    
    # Risk Thresholds
    ACADEMIC_RISK_CGPA_THRESHOLD: float = 6.0      # Out of 10
    ACADEMIC_RISK_ATTENDANCE_THRESHOLD: float = 75.0 # Percent
    ACADEMIC_RISK_LMS_THRESHOLD: float = 60.0       # Percent
    
    PLACEMENT_RISK_READINESS_THRESHOLD: float = 60.0 # Percent
    PLACEMENT_RISK_SKILL_THRESHOLD: float = 55.0     # Percent

settings = Settings()

