from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="pxss-bid-agent", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    backend_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="BACKEND_CORS_ORIGINS",
    )

    database_url: str = Field(
        default="postgresql+psycopg://pxss:pxss_dev_password@localhost:5432/pxss_bid_agent",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_root_user: str = Field(default="pxss_minio", alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(
        default="pxss_minio_password",
        alias="MINIO_ROOT_PASSWORD",
    )
    minio_bucket: str = Field(default="bid-agent", alias="MINIO_BUCKET")

    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_simple_model: str = Field(default="deepseek-v4-flash", alias="LLM_SIMPLE_MODEL")
    llm_complex_model: str = Field(default="deepseek-v4-pro", alias="LLM_COMPLEX_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    model_config_encryption_key: str = Field(default="", alias="MODEL_CONFIG_ENCRYPTION_KEY")
    model_config_encryption_key_version: str = Field(default="v1", alias="MODEL_CONFIG_ENCRYPTION_KEY_VERSION")
    run_tasks_inline: bool = Field(default=True, alias="RUN_TASKS_INLINE")
    matrix_fork_join_enabled: bool = Field(default=True, alias="MATRIX_FORK_JOIN_ENABLED")
    matrix_fork_join_max_workers: int = Field(default=4, alias="MATRIX_FORK_JOIN_MAX_WORKERS")
    matrix_fork_join_min_sections: int = Field(default=4, alias="MATRIX_FORK_JOIN_MIN_SECTIONS")

    frontend_dist_dir: str = Field(default="", alias="FRONTEND_DIST_DIR")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


settings = Settings()
