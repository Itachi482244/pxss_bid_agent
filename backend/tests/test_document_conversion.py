from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services import document_conversion
from app.services.document_conversion import (
    LegacyDocConversionError,
    convert_legacy_doc_to_docx,
)


class _FakeResponse:
    def __init__(self, *, status_code: int, content: bytes = b"", json_body: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self.content = content
        self._json_body = json_body
        self.text = text

    def json(self) -> dict:
        if self._json_body is None:
            raise ValueError("no json body")
        return self._json_body


def _install_fake_client(monkeypatch, *, response: _FakeResponse | None = None, raises: Exception | None = None):
    captured: dict[str, object] = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> None:
            return None

        def post(self, url, *, content, params=None, headers=None):
            captured["url"] = url
            captured["content"] = content
            captured["params"] = params
            captured["headers"] = headers
            if raises is not None:
                raise raises
            assert response is not None
            return response

    monkeypatch.setattr(document_conversion.httpx, "Client", _FakeClient)
    return captured


@pytest.fixture(autouse=True)
def _http_mode(monkeypatch):
    monkeypatch.setattr(settings, "legacy_doc_conversion_enabled", True)
    monkeypatch.setattr(settings, "legacy_doc_converter_mode", "http")
    monkeypatch.setattr(settings, "legacy_doc_converter_url", "http://converter:2004/")
    monkeypatch.setattr(settings, "legacy_doc_conversion_timeout_seconds", 30.0)


def test_http_mode_returns_converted_bytes(monkeypatch) -> None:
    captured = _install_fake_client(
        monkeypatch,
        response=_FakeResponse(status_code=200, content=b"PK\x03\x04docx-bytes"),
    )

    result = convert_legacy_doc_to_docx(b"\xd0\xcf\x11\xe0doc", filename="招标文件.doc")

    assert result == b"PK\x03\x04docx-bytes"
    assert captured["url"] == "http://converter:2004/convert"
    assert captured["params"] == {"filename": "招标文件.doc"}
    assert captured["content"] == b"\xd0\xcf\x11\xe0doc"


def test_http_mode_chinese_filename_through_real_httpx(monkeypatch) -> None:
    # 用真实 httpx + MockTransport 走完整请求构造，确保中文文件名不再触发
    # latin-1 header 编码错误（X-Filename 回归）。
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["filename"] = request.url.params.get("filename")
        captured["content"] = request.content
        return httpx.Response(200, content=b"PK\x03\x04ok")

    real_client_cls = httpx.Client

    def fake_client(**kwargs):  # noqa: ARG001
        return real_client_cls(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(document_conversion.httpx, "Client", fake_client)

    result = convert_legacy_doc_to_docx(
        b"\xd0\xcf\x11\xe0doc",
        filename="仓顶面吊顶隔热降温改造招标文件.doc",
    )

    assert result == b"PK\x03\x04ok"
    assert captured["filename"] == "仓顶面吊顶隔热降温改造招标文件.doc"
    assert captured["content"] == b"\xd0\xcf\x11\xe0doc"


def test_http_mode_missing_url_reports_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "legacy_doc_converter_url", "")

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERTER_UNAVAILABLE"


def test_http_mode_connection_error_reports_unavailable(monkeypatch) -> None:
    _install_fake_client(monkeypatch, raises=httpx.ConnectError("connection refused"))

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERTER_UNAVAILABLE"


def test_http_mode_timeout_reports_timeout(monkeypatch) -> None:
    _install_fake_client(monkeypatch, raises=httpx.ReadTimeout("timed out"))

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERSION_TIMEOUT"


def test_http_mode_service_504_reports_timeout(monkeypatch) -> None:
    _install_fake_client(
        monkeypatch,
        response=_FakeResponse(status_code=504, json_body={"error": "conversion timed out", "code": "CONVERSION_TIMEOUT"}),
    )

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERSION_TIMEOUT"


def test_http_mode_service_503_reports_unavailable(monkeypatch) -> None:
    _install_fake_client(
        monkeypatch,
        response=_FakeResponse(status_code=503, json_body={"error": "soffice not found", "code": "CONVERTER_UNAVAILABLE"}),
    )

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERTER_UNAVAILABLE"


def test_http_mode_non_200_reports_failed_with_detail(monkeypatch) -> None:
    _install_fake_client(
        monkeypatch,
        response=_FakeResponse(status_code=502, json_body={"error": "soffice failed: boom", "code": "CONVERSION_FAILED"}),
    )

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERSION_FAILED"
    assert "boom" in str(exc.value)


def test_http_mode_empty_body_reports_empty(monkeypatch) -> None:
    _install_fake_client(monkeypatch, response=_FakeResponse(status_code=200, content=b""))

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERSION_EMPTY"


def test_disabled_short_circuits_before_http(monkeypatch) -> None:
    monkeypatch.setattr(settings, "legacy_doc_conversion_enabled", False)

    with pytest.raises(LegacyDocConversionError) as exc:
        convert_legacy_doc_to_docx(b"doc", filename="a.doc")
    assert exc.value.code == "LEGACY_DOC_CONVERSION_DISABLED"
