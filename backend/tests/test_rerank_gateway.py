from __future__ import annotations

from app.core.config import settings
from app.services import rerank_gateway
from app.services.rerank_gateway import rerank_texts


def test_infinity_rerank_scores_are_normalized(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rerank_enabled", True)
    monkeypatch.setattr(settings, "rerank_provider", "infinity")
    monkeypatch.setattr(settings, "rerank_model", "BAAI/bge-reranker-base")
    monkeypatch.setattr(settings, "rerank_fallback_enabled", True)

    def fake_rerank_with_infinity(query: str, documents: list[str]) -> tuple[list[tuple[int, float]], str, str]:
        assert query
        assert len(documents) == 2
        return [(0, 0.91), (1, 0.12)], "BAAI/bge-reranker-base", "infinity_rerank"

    monkeypatch.setattr(rerank_gateway, "_rerank_with_infinity", fake_rerank_with_infinity)

    scores = rerank_texts("营业执照", ["营业执照材料", "财务审计材料"])

    assert [score.index for score in scores] == [0, 1]
    assert scores[0].provider == "infinity_baai_bge_reranker_base"
    assert scores[0].runtime_provider == "infinity_rerank"
    assert scores[0].model_name == "BAAI/bge-reranker-base"
    assert scores[0].score > scores[1].score
    assert scores[0].fallback_used is False


def test_infinity_rerank_falls_back_to_local_overlap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rerank_enabled", True)
    monkeypatch.setattr(settings, "rerank_provider", "infinity")
    monkeypatch.setattr(settings, "rerank_model", "BAAI/bge-reranker-base")
    monkeypatch.setattr(settings, "rerank_fallback_enabled", True)

    def fake_rerank_with_infinity(_: str, __: list[str]) -> tuple[list[tuple[int, float]], str, str]:
        raise RuntimeError("infinity rerank unavailable")

    monkeypatch.setattr(rerank_gateway, "_rerank_with_infinity", fake_rerank_with_infinity)

    scores = rerank_texts(
        "一级建造师",
        ["一级建造师", "企业营业执照"],
        base_scores=[0.3, 0.3],
    )

    assert scores[0].index == 0
    assert scores[0].score > scores[1].score
    assert scores[0].fallback_used is True
    assert "infinity rerank unavailable" in (scores[0].error_message or "")
