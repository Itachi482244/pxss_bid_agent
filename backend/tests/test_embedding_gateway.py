from __future__ import annotations

from app.core.config import settings
from app.services import embedding_gateway
from app.services.embedding_gateway import EMBEDDING_DIMENSIONS, embed_text


def test_infinity_oversized_embedding_is_fit_to_768_dimensions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "infinity")
    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-base-zh-v1.5")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", True)

    def fake_embed_with_infinity(text: str) -> tuple[list[float], str, int]:
        assert text
        return [float(index + 1) for index in range(1024)], "BAAI/bge-base-zh-v1.5", 1024

    monkeypatch.setattr(embedding_gateway, "_embed_with_infinity", fake_embed_with_infinity)

    result = embed_text("投标人须提供有效营业执照。")

    assert result.provider == "infinity_baai_bge_base_zh_v1.5_768"
    assert result.runtime_provider == "infinity"
    assert result.model_name == "BAAI/bge-base-zh-v1.5"
    assert result.source_dimensions == 1024
    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert result.fallback_used is False


def test_infinity_bge_base_zh_embedding_is_used(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "infinity")
    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-base-zh-v1.5")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", True)

    def fake_embed_with_infinity(text: str) -> tuple[list[float], str, int]:
        assert text
        return [float(index + 1) for index in range(768)], "BAAI/bge-base-zh-v1.5", 768

    monkeypatch.setattr(embedding_gateway, "_embed_with_infinity", fake_embed_with_infinity)

    result = embed_text("投标人须提供有效营业执照。")

    assert result.provider == "infinity_baai_bge_base_zh_v1.5_768"
    assert result.runtime_provider == "infinity"
    assert result.model_name == "BAAI/bge-base-zh-v1.5"
    assert result.source_dimensions == 768
    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert result.fallback_used is False


def test_infinity_embedding_falls_back_to_local(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "infinity")
    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-base-zh-v1.5")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", True)

    def fake_embed_with_infinity(_: str) -> tuple[list[float], str, int]:
        raise RuntimeError("infinity unavailable")

    monkeypatch.setattr(embedding_gateway, "_embed_with_infinity", fake_embed_with_infinity)

    result = embed_text("项目经理须具备一级建造师资格。")

    assert result.provider == "infinity_baai_bge_base_zh_v1.5_768"
    assert result.runtime_provider == "local_hash"
    assert len(result.vector) == EMBEDDING_DIMENSIONS
    assert result.fallback_used is True
    assert "infinity unavailable" in (result.error_message or "")
