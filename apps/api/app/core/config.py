from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "local")
        self.app_secret_key = os.getenv("APP_SECRET_KEY", "change-me-in-local-env")
        self.access_token_expire_seconds = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "28800"))
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://ai_brain:password@localhost:5432/ai_brain",
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.model_gateway_base_url = os.getenv("MODEL_GATEWAY_BASE_URL", "")
        self.model_gateway_api_key = os.getenv("MODEL_GATEWAY_API_KEY", "")
        self.model_gateway_default_chat_model = os.getenv(
            "MODEL_GATEWAY_DEFAULT_CHAT_MODEL",
            "local-chat",
        )
        self.model_gateway_default_embedding_model = os.getenv(
            "MODEL_GATEWAY_DEFAULT_EMBEDDING_MODEL",
            "local-embedding",
        )
        self.vector_dimension = int(os.getenv("VECTOR_DIMENSION", "1536"))
        self.cors_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def model_gateway_status(self) -> str:
        if self.model_gateway_base_url and self.model_gateway_api_key:
            return "configured"
        return "local_fallback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
