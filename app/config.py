import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Paths
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    PLACES_JSON: str = os.path.join(DATA_DIR, 'places.json')
    
    # API Settings
    API_TITLE: str = "BD Tour Guide API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI-powered tour guide for Bangladesh"
    
    # CORS
    CORS_ORIGINS: list = ["*"]  # Update in production
    
    class Config:
        env_file = ".env"

settings = Settings()
EMBED_MODEL = "gemini-embedding-001"  # latest free embedding model
LLM_MODEL = "gemini-2.0-flash"           # latest free chat model
TOP_K = 5                                # number of relevant spots to retrieve
FAISS_INDEX_PATH = "../data/faiss_index"