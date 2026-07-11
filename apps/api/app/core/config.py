from __future__ import annotations

import os
from functools import lru_cache


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes"}


def _env_key_value_map(name: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in os.getenv(name, "").split(","):
        text = item.strip()
        if not text:
            continue
        separator = "=" if "=" in text else ":"
        if separator not in text:
            continue
        key, value = text.split(separator, 1)
        if key.strip() and value.strip():
            mapping[key.strip()] = value.strip()
    return mapping


def _env_csv_set(name: str, default: str) -> set[str]:
    return {
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    }


DEFAULT_APP_SECRET_KEY = "change-me-in-local-env"
DEFAULT_KNOWLEDGE_UPLOAD_ALLOWED_EXTENSIONS = (
    ".csv,.jpeg,.jpg,.json,.md,.markdown,.pdf,.png,.tif,.tiff,.txt,.webp"
)
DEFAULT_KNOWLEDGE_UPLOAD_ALLOWED_MIME_TYPES = (
    "application/json,application/octet-stream,application/pdf,"
    "image/jpeg,image/png,image/tiff,image/webp,"
    "text/csv,text/markdown,text/plain,text/x-markdown"
)
LOCAL_APP_ENVIRONMENTS = {"dev", "development", "local"}
TEST_APP_ENVIRONMENTS = {"pytest", "test", "testing"}
LOCAL_NETWORK_CORS_ENVIRONMENTS = LOCAL_APP_ENVIRONMENTS | TEST_APP_ENVIRONMENTS
LOCAL_NETWORK_CORS_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost|"
    r"127(?:\.\d{1,3}){3}|"
    r"0\.0\.0\.0|"
    r"10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
    r")(?::\d+)?$"
)


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "local")
        self.allow_seeded_users = _env_bool("ALLOW_SEEDED_USERS", "")
        self.app_secret_key = os.getenv("APP_SECRET_KEY", DEFAULT_APP_SECRET_KEY)
        self.access_token_expire_seconds = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "28800"))
        default_login_challenge_enabled = (
            "false"
            if self.app_env.lower() in TEST_APP_ENVIRONMENTS
            else "true"
        )
        self.login_challenge_enabled = _env_bool(
            "LOGIN_CHALLENGE_ENABLED",
            default_login_challenge_enabled,
        )
        self.login_challenge_ttl_seconds = int(
            os.getenv("LOGIN_CHALLENGE_TTL_SECONDS", "300"),
        )
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://ai_brain:password@localhost:5432/ai_brain",
        )
        self.database_pool_max_size = int(os.getenv("DATABASE_POOL_MAX_SIZE", "5"))
        self.dashboard_cache_ttl_seconds = int(os.getenv("DASHBOARD_CACHE_TTL_SECONDS", "30"))
        self.dashboard_slow_threshold_ms = int(os.getenv("DASHBOARD_SLOW_THRESHOLD_MS", "500"))
        self.persistence_mode = os.getenv("PERSISTENCE_MODE", "postgres").lower()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.object_storage_provider = os.getenv("OBJECT_STORAGE_PROVIDER", "local").lower()
        self.object_storage_local_dir = os.getenv(
            "OBJECT_STORAGE_LOCAL_DIR",
            "/tmp/e-ai-brain-object-storage",
        )
        self.object_storage_bucket = os.getenv("OBJECT_STORAGE_BUCKET", "ai-brain-knowledge")
        self.object_storage_endpoint = os.getenv("OBJECT_STORAGE_ENDPOINT", "")
        self.object_storage_access_key = os.getenv("OBJECT_STORAGE_ACCESS_KEY", "")
        self.object_storage_secret_key = os.getenv("OBJECT_STORAGE_SECRET_KEY", "")
        self.object_storage_secure = _env_bool("OBJECT_STORAGE_SECURE")
        self.knowledge_upload_max_bytes = int(
            os.getenv("KNOWLEDGE_UPLOAD_MAX_BYTES", str(50 * 1024 * 1024)),
        )
        self.knowledge_upload_presign_expires_seconds = int(
            os.getenv("KNOWLEDGE_UPLOAD_PRESIGN_EXPIRES_SECONDS", "900"),
        )
        self.knowledge_upload_allowed_extensions = _env_csv_set(
            "KNOWLEDGE_UPLOAD_ALLOWED_EXTENSIONS",
            DEFAULT_KNOWLEDGE_UPLOAD_ALLOWED_EXTENSIONS,
        )
        self.knowledge_upload_allowed_mime_types = _env_csv_set(
            "KNOWLEDGE_UPLOAD_ALLOWED_MIME_TYPES",
            DEFAULT_KNOWLEDGE_UPLOAD_ALLOWED_MIME_TYPES,
        )
        self.knowledge_preview_max_chars = int(
            os.getenv("KNOWLEDGE_PREVIEW_MAX_CHARS", "4000"),
        )
        default_import_worker_enabled = (
            "false" if self.app_env.lower() in {"test", "testing", "pytest"} else "true"
        )
        self.knowledge_import_worker_enabled = _env_bool(
            "KNOWLEDGE_IMPORT_WORKER_ENABLED",
            default_import_worker_enabled,
        )
        self.knowledge_import_worker_poll_interval_seconds = float(
            os.getenv("KNOWLEDGE_IMPORT_WORKER_POLL_INTERVAL_SECONDS", "1.0"),
        )
        self.knowledge_import_worker_lock_ttl_seconds = float(
            os.getenv("KNOWLEDGE_IMPORT_WORKER_LOCK_TTL_SECONDS", "300.0"),
        )
        self.execution_worker_embedded_enabled = _env_bool(
            "EXECUTION_WORKER_EMBEDDED_ENABLED",
            "false",
        )
        self.execution_worker_poll_interval_seconds = float(
            os.getenv("EXECUTION_WORKER_POLL_INTERVAL_SECONDS", "5.0"),
        )
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
        self.gbrain_base_url = os.getenv("GBRAIN_BASE_URL", "")
        self.gbrain_api_key = os.getenv("GBRAIN_API_KEY", "")
        self.code_review_executor_type = os.getenv(
            "CODE_REVIEW_EXECUTOR_TYPE",
            "claude_code_skill",
        ).lower()
        self.code_review_executor_name = os.getenv("CODE_REVIEW_EXECUTOR_NAME", "code-review")
        self.code_review_executor_command = os.getenv("CODE_REVIEW_EXECUTOR_COMMAND", "")
        self.code_review_executor_timeout_seconds = int(
            os.getenv("CODE_REVIEW_EXECUTOR_TIMEOUT_SECONDS", "180")
        )
        self.vector_dimension = int(os.getenv("VECTOR_DIMENSION", "1536"))
        self.cors_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        default_local_network_cors = (
            "true" if self.app_env.lower() in LOCAL_NETWORK_CORS_ENVIRONMENTS else "false"
        )
        self.cors_allow_local_network_origins = _env_bool(
            "CORS_ALLOW_LOCAL_NETWORK_ORIGINS",
            default_local_network_cors,
        )
        self.dingtalk_login_enabled = _env_bool("DINGTALK_LOGIN_ENABLED")
        self.dingtalk_client_id = os.getenv("DINGTALK_CLIENT_ID", "")
        self.dingtalk_client_secret = os.getenv("DINGTALK_CLIENT_SECRET", "")
        self.dingtalk_client_secret_ref = os.getenv("DINGTALK_CLIENT_SECRET_REF", "")
        self.dingtalk_redirect_uri = os.getenv("DINGTALK_REDIRECT_URI", "")
        self.dingtalk_bind_redirect_uri = os.getenv("DINGTALK_BIND_REDIRECT_URI", "")
        self.dingtalk_allowed_corp_ids = os.getenv("DINGTALK_ALLOWED_CORP_IDS", "")
        self.dingtalk_corp_name_map = _env_key_value_map("DINGTALK_CORP_NAME_MAP")
        self.dingtalk_auto_provision = _env_bool("DINGTALK_AUTO_PROVISION")
        self.dingtalk_auto_provision_role = os.getenv(
            "DINGTALK_AUTO_PROVISION_ROLE",
            "viewer",
        )
        self.dingtalk_pending_approval = _env_bool("DINGTALK_PENDING_APPROVAL")
        self.dingtalk_auth_url = os.getenv(
            "DINGTALK_AUTH_URL",
            "https://login.dingtalk.com/oauth2/auth",
        )
        self.dingtalk_token_url = os.getenv(
            "DINGTALK_TOKEN_URL",
            "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
        )
        self.dingtalk_userinfo_url = os.getenv(
            "DINGTALK_USERINFO_URL",
            "https://api.dingtalk.com/v1.0/contact/users/me",
        )
        self.dingtalk_frontend_callback_path = os.getenv(
            "DINGTALK_FRONTEND_CALLBACK_PATH",
            "/login/dingtalk/callback",
        )
        self.dingtalk_frontend_base_url = os.getenv("DINGTALK_FRONTEND_BASE_URL", "")

    @property
    def normalized_app_env(self) -> str:
        return self.app_env.lower()

    @property
    def is_local_env(self) -> bool:
        return self.normalized_app_env in LOCAL_APP_ENVIRONMENTS

    @property
    def is_test_env(self) -> bool:
        return self.normalized_app_env in TEST_APP_ENVIRONMENTS

    @property
    def is_local_or_test_env(self) -> bool:
        return self.is_local_env or self.is_test_env

    @property
    def app_secret_key_is_placeholder(self) -> bool:
        secret = self.app_secret_key.strip().lower()
        return (
            not secret
            or secret == DEFAULT_APP_SECRET_KEY
            or "change-me" in secret
            or secret.startswith("replace-with")
            or secret in {"local-secret", "<local-secret>"}
        )

    def validate_runtime_security(self) -> None:
        if self.is_local_or_test_env:
            return
        if self.app_secret_key_is_placeholder or len(self.app_secret_key.strip()) < 32:
            raise RuntimeError(
                "APP_SECRET_KEY must be set to a non-placeholder value with at least "
                "32 characters outside local/test environments",
            )
        if self.allow_seeded_users:
            raise RuntimeError(
                "ALLOW_SEEDED_USERS is only allowed in local/test environments",
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        if self.cors_allow_local_network_origins:
            return LOCAL_NETWORK_CORS_ORIGIN_REGEX
        return None

    @property
    def dingtalk_allowed_corp_id_set(self) -> set[str]:
        return {
            corp_id.strip()
            for corp_id in self.dingtalk_allowed_corp_ids.split(",")
            if corp_id.strip()
        }

    @property
    def dingtalk_client_secret_value(self) -> str:
        if self.dingtalk_client_secret:
            return self.dingtalk_client_secret
        if self.dingtalk_client_secret_ref.startswith("env:"):
            return os.getenv(self.dingtalk_client_secret_ref.removeprefix("env:"), "")
        return ""

    @property
    def dingtalk_login_configured(self) -> bool:
        return all(
            [
                self.dingtalk_login_enabled,
                self.dingtalk_client_id,
                self.dingtalk_client_secret_value,
                self.dingtalk_redirect_uri,
            ]
        )

    @property
    def dingtalk_bind_redirect_uri_value(self) -> str:
        if self.dingtalk_bind_redirect_uri:
            return self.dingtalk_bind_redirect_uri
        if self.dingtalk_redirect_uri.endswith("/callback"):
            return f"{self.dingtalk_redirect_uri.removesuffix('/callback')}/bind/callback"
        return self.dingtalk_redirect_uri

    @property
    def model_gateway_status(self) -> str:
        if self.model_gateway_base_url and self.model_gateway_api_key:
            return "configured"
        return "not_configured"

    @property
    def long_memory_status(self) -> str:
        if self.gbrain_base_url and self.gbrain_api_key:
            return "configured"
        return "not_configured"


@lru_cache
def get_settings() -> Settings:
    return Settings()
