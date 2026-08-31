from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration via environment variables.
    Defaults are provided for local development. Never store secrets directly in this file.
    """
    APP_ENV: str = "dev"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/secure_exam"
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_SECURITY_PROTOCOL: str = "PLAINTEXT"
    
    # AWS KMS
    AWS_KMS_KEY_ID: str = "alias/secure-exam-dev"
    AWS_REGION: str = "us-east-1"
    
    # JWT & Auth
    JWT_SECRET_KEY: str = "local-dev-secret-do-not-use-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 30
    
    # Storage
    BLOB_STORAGE_PATH: str = "/tmp/secure_exam_blobs"
    S3_BUCKET: str = ""
    
    # Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    RATE_LIMIT: str = "100/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
