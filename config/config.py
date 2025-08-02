import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Authentication
    HACKRX_API_TOKEN: str = Field(..., env="HACKRX_API_TOKEN")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google Gemini Configuration
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-pro"

    # Vector Database Configuration
    PINECONE_API_KEY: Optional[str] = Field(None, env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = "document-embeddings"

    # Database Configuration
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")

    # Document Processing
    MAX_FILE_SIZE: int = 50000000  # 50MB
    ALLOWED_EXTENSIONS: list = ["pdf", "docx"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Embedding Configuration
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    TOP_K_RESULTS: int = 10

    # Response Configuration
    MAX_RESPONSE_LENGTH: int = 2000
    CONFIDENCE_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()
