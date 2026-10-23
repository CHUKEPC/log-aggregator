"""Configuration module for the Log Aggregator service.

Loads settings from environment variables and provides centralized configuration
management across the application.
"""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "log-aggregator"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Authentication
    SECRET_KEY: str = "change-me-to-a-secure-secret-key-at-least-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpassword"

    # API Keys mapping for services: "service_name:key,service_b:key2"
    API_KEYS: dict[str, str] = Field(
        default_factory=lambda: {
            "auth-service": "secret-auth-key",
            "payment-service": "secret-payment-key",
            "frontend": "secret-frontend-key",
        }
    )

    # Elasticsearch Configuration
    ELASTICSEARCH_HOSTS: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "logs"
    ELASTICSEARCH_USER: str | None = None
    ELASTICSEARCH_PASSWORD: str | None = None
    ELASTICSEARCH_VERIFY_CERTS: bool = False
    USE_MEMORY_STORAGE: bool = False

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 600

    # Retention Policy (days to retain logs; 0 = keep indefinitely)
    RETENTION_DAYS: int = 30

    # TCP Socket Receiver
    TCP_SERVER_ENABLED: bool = False
    TCP_SERVER_HOST: str = "0.0.0.0"
    TCP_SERVER_PORT: int = 9000

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, value: Any) -> dict[str, str]:
        """Parse comma-separated 'service:key' string or return dictionary."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            result: dict[str, str] = {}
            pairs = value.split(",")
            for pair in pairs:
                trimmed = pair.strip()
                if not trimmed:
                    continue
                if ":" in trimmed:
                    service, key = trimmed.split(":", 1)
                    result[service.strip()] = key.strip()
            return result
        return {}


settings = Settings()
