from functools import cached_property
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
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
    # Aliyun OCR (读光 OCR / ocr-api20210707, RecognizeAdvanced 高精全文+表格)
    aliyun_ocr_enabled: bool = Field(default=False, alias="ALIYUN_OCR_ENABLED")
    aliyun_ocr_access_key_id: str = Field(default="", alias="ALIYUN_OCR_ACCESS_KEY_ID")
    aliyun_ocr_access_key_secret: str = Field(default="", alias="ALIYUN_OCR_ACCESS_KEY_SECRET")
    aliyun_ocr_endpoint: str = Field(
        default="ocr-api.cn-hangzhou.aliyuncs.com",
        alias="ALIYUN_OCR_ENDPOINT",
    )
    aliyun_ocr_timeout_seconds: float = Field(default=30.0, alias="ALIYUN_OCR_TIMEOUT_SECONDS")

    # Embedding 推理服务。provider: infinity | local
    # 默认走 Infinity 的 OpenAI 风格 /embeddings（Mac 开发 / Linux 部署同一套）。
    # 模型 bge-base-zh-v1.5：中文专精，102M，输出 768 维（pgvector 列对齐 768）。
    embedding_provider: str = Field(default="infinity", alias="EMBEDDING_PROVIDER")
    embedding_base_url: str = Field(default="http://localhost:7997", alias="EMBEDDING_BASE_URL")
    embedding_model: str = Field(default="BAAI/bge-base-zh-v1.5", alias="EMBEDDING_MODEL")
    embedding_timeout_seconds: float = Field(default=30.0, alias="EMBEDDING_TIMEOUT_SECONDS")
    embedding_fallback_enabled: bool = Field(default=True, alias="EMBEDDING_FALLBACK_ENABLED")
    # Rerank 推理服务。provider: infinity | local
    rerank_enabled: bool = Field(default=True, alias="RERANK_ENABLED")
    rerank_provider: str = Field(default="infinity", alias="RERANK_PROVIDER")
    rerank_base_url: str = Field(default="http://localhost:7997", alias="RERANK_BASE_URL")
    rerank_model: str = Field(default="BAAI/bge-reranker-base", alias="RERANK_MODEL")
    rerank_timeout_seconds: float = Field(default=30.0, alias="RERANK_TIMEOUT_SECONDS")
    rerank_top_k: int = Field(default=50, alias="RERANK_TOP_K")
    rerank_fallback_enabled: bool = Field(default=True, alias="RERANK_FALLBACK_ENABLED")

    source_page_image_format: str = Field(default="jpeg", alias="SOURCE_PAGE_IMAGE_FORMAT")
    source_page_image_max_width: int = Field(default=1200, alias="SOURCE_PAGE_IMAGE_MAX_WIDTH")
    source_page_image_jpeg_quality: int = Field(default=70, alias="SOURCE_PAGE_IMAGE_JPEG_QUALITY")
    source_page_image_render_scale: float = Field(default=2.0, alias="SOURCE_PAGE_IMAGE_RENDER_SCALE")

    run_tasks_inline: bool = Field(default=True, alias="RUN_TASKS_INLINE")
    matrix_fork_join_enabled: bool = Field(default=True, alias="MATRIX_FORK_JOIN_ENABLED")
    matrix_fork_join_max_workers: int = Field(default=4, alias="MATRIX_FORK_JOIN_MAX_WORKERS")
    matrix_fork_join_min_sections: int = Field(default=4, alias="MATRIX_FORK_JOIN_MIN_SECTIONS")

    frontend_dist_dir: str = Field(default="", alias="FRONTEND_DIST_DIR")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


settings = Settings()
