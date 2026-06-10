"""OCR 纯解析逻辑单测：不触达阿里云，无需 AccessKey。"""

from __future__ import annotations

import pytest

from app.services.ocr import (
    ALIYUN_PROVIDER,
    OcrNotConfiguredError,
    get_ocr_client,
    parse_recognize_advanced_data,
)


def test_parse_plain_text():
    result = parse_recognize_advanced_data({"content": "营业执照\n统一社会信用代码 91310000XXX"})
    assert result.provider == ALIYUN_PROVIDER
    assert "营业执照" in result.text
    assert result.tables == []


def test_parse_strips_and_handles_empty():
    assert parse_recognize_advanced_data({}).text == ""
    assert parse_recognize_advanced_data({"content": "  \n  "}).text == ""


def test_reconstruct_table_from_cell_infos():
    data = {
        "content": "资质等级表",
        "prism_tablesInfo": [
            {
                "xCellSize": 2,
                "yCellSize": 2,
                "cellInfos": [
                    {"word": "资质名称", "xsc": 0, "xec": 0, "ysc": 0, "yec": 0},
                    {"word": "等级", "xsc": 1, "xec": 1, "ysc": 0, "yec": 0},
                    {"word": "建筑工程施工总承包", "xsc": 0, "xec": 0, "ysc": 1, "yec": 1},
                    {"word": "一级", "xsc": 1, "xec": 1, "ysc": 1, "yec": 1},
                ],
            }
        ],
    }
    result = parse_recognize_advanced_data(data)
    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.rows == [
        ["资质名称", "等级"],
        ["建筑工程施工总承包", "一级"],
    ]
    assert table.to_text() == "资质名称 | 等级\n建筑工程施工总承包 | 一级"


def test_table_size_inferred_when_cellsize_missing():
    data = {
        "prism_tablesInfo": [
            {
                "cellInfos": [
                    {"word": "A", "xsc": 0, "ysc": 0},
                    {"word": "B", "xsc": 2, "ysc": 1},
                ]
            }
        ]
    }
    table = parse_recognize_advanced_data(data).tables[0]
    assert len(table.rows) == 2
    assert len(table.rows[0]) == 3
    assert table.rows[0][0] == "A"
    assert table.rows[1][2] == "B"


def test_confidence_normalized_from_prob():
    data = {
        "content": "x",
        "prism_wordsInfo": [{"prob": 96}, {"prob": 92}, {"word": "无prob"}],
    }
    result = parse_recognize_advanced_data(data)
    assert result.confidence == pytest.approx(0.94, abs=1e-6)


def test_confidence_none_when_no_prob():
    assert parse_recognize_advanced_data({"content": "x"}).confidence is None


def test_get_ocr_client_requires_enabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "aliyun_ocr_enabled", False)
    with pytest.raises(OcrNotConfiguredError):
        get_ocr_client()


def test_get_ocr_client_requires_credentials(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "aliyun_ocr_enabled", True)
    monkeypatch.setattr(settings, "aliyun_ocr_access_key_id", "")
    monkeypatch.setattr(settings, "aliyun_ocr_access_key_secret", "")
    with pytest.raises(OcrNotConfiguredError):
        get_ocr_client()
