from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.core.config import settings


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class LegacyDocConversionError(Exception):
    def __init__(self, message: str, *, code: str = "LEGACY_DOC_CONVERSION_FAILED") -> None:
        super().__init__(message)
        self.code = code


def _find_converter() -> str | None:
    configured = settings.legacy_doc_converter_path.strip()
    if configured:
        return configured
    return shutil.which("soffice") or shutil.which("libreoffice")


def _summarize_process_output(value: str) -> str:
    text = " ".join(value.split())
    return text[:600]


def convert_legacy_doc_to_docx(data: bytes, *, filename: str = "source.doc") -> bytes:
    """Convert legacy binary Word .doc bytes to .docx.

    Two backends, selected by ``LEGACY_DOC_CONVERTER_MODE``:
    - ``http`` (default): call the LibreOffice converter sidecar over HTTP
      (matches how the backend already talks to the Infinity sidecar).
    - ``subprocess``: call a local/baked-in LibreOffice/soffice binary.
    """
    if not settings.legacy_doc_conversion_enabled:
        raise LegacyDocConversionError(
            "旧版 .doc 自动转换已关闭，请先手工转换为 .docx",
            code="LEGACY_DOC_CONVERSION_DISABLED",
        )

    mode = settings.legacy_doc_converter_mode.strip().lower() or "subprocess"
    if mode == "http":
        return _convert_via_http(data, filename=filename)
    return _convert_via_subprocess(data, filename=filename)


def _convert_via_http(data: bytes, *, filename: str) -> bytes:
    base_url = settings.legacy_doc_converter_url.strip().rstrip("/")
    if not base_url:
        raise LegacyDocConversionError(
            "旧版 .doc HTTP 转换未配置 LEGACY_DOC_CONVERTER_URL",
            code="LEGACY_DOC_CONVERTER_UNAVAILABLE",
        )

    timeout = httpx.Timeout(
        settings.legacy_doc_conversion_timeout_seconds,
        connect=min(10.0, settings.legacy_doc_conversion_timeout_seconds),
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            # 文件名走 query 参数：真实招标文件名多为中文，放进 HTTP header 会触发
            # latin-1 编码错误（且不是 httpx.HTTPError），故由 httpx 做百分号编码、
            # sidecar 端 parse_qs 按 utf-8 解回。
            response = client.post(
                f"{base_url}/convert",
                content=data,
                params={"filename": filename or "source.doc"},
                headers={"Content-Type": "application/octet-stream"},
            )
    except httpx.TimeoutException as exc:
        raise LegacyDocConversionError(
            "旧版 .doc 自动转换超时，请手工转换为 .docx 后重新上传",
            code="LEGACY_DOC_CONVERSION_TIMEOUT",
        ) from exc
    except httpx.HTTPError as exc:
        raise LegacyDocConversionError(
            f"旧版 .doc 转换服务不可用：{_summarize_process_output(str(exc))}",
            code="LEGACY_DOC_CONVERTER_UNAVAILABLE",
        ) from exc

    if response.status_code == 503:
        raise LegacyDocConversionError(
            "旧版 .doc 转换服务未就绪（容器内缺少 LibreOffice）",
            code="LEGACY_DOC_CONVERTER_UNAVAILABLE",
        )
    if response.status_code == 504:
        raise LegacyDocConversionError(
            "旧版 .doc 自动转换超时，请手工转换为 .docx 后重新上传",
            code="LEGACY_DOC_CONVERSION_TIMEOUT",
        )
    if response.status_code != 200:
        detail = _extract_http_error_detail(response)
        raise LegacyDocConversionError(
            f"旧版 .doc 自动转换失败：{detail}",
            code="LEGACY_DOC_CONVERSION_FAILED",
        )

    converted = response.content
    if not converted:
        raise LegacyDocConversionError(
            "旧版 .doc 自动转换失败：转换结果为空",
            code="LEGACY_DOC_CONVERSION_EMPTY",
        )
    return converted


def _extract_http_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("error"):
        return _summarize_process_output(str(payload["error"]))
    return _summarize_process_output(response.text) or f"HTTP {response.status_code}"


def _convert_via_subprocess(data: bytes, *, filename: str) -> bytes:
    converter = _find_converter()
    if converter is None:
        raise LegacyDocConversionError(
            "旧版 .doc 自动转换依赖 LibreOffice/soffice，当前环境未安装转换器",
            code="LEGACY_DOC_CONVERTER_UNAVAILABLE",
        )

    safe_stem = Path(filename or "source.doc").stem or "source"
    with tempfile.TemporaryDirectory(prefix="bid-agent-doc-convert-") as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / f"{safe_stem}.doc"
        output_dir = tmp_dir / "out"
        profile_dir = tmp_dir / "lo-profile"
        output_dir.mkdir()
        profile_dir.mkdir()
        input_path.write_bytes(data)

        command = [
            converter,
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--nodefault",
            "--nolockcheck",
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=settings.legacy_doc_conversion_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise LegacyDocConversionError(
                "旧版 .doc 自动转换超时，请手工转换为 .docx 后重新上传",
                code="LEGACY_DOC_CONVERSION_TIMEOUT",
            ) from exc

        output_path = output_dir / f"{safe_stem}.docx"
        if completed.returncode != 0 or not output_path.exists():
            candidates = sorted(output_dir.glob("*.docx"))
            if completed.returncode == 0 and candidates:
                output_path = candidates[0]
            else:
                stdout = _summarize_process_output(completed.stdout)
                stderr = _summarize_process_output(completed.stderr)
                detail = stderr or stdout or "转换器未生成 .docx 文件"
                raise LegacyDocConversionError(
                    f"旧版 .doc 自动转换失败：{detail}",
                    code="LEGACY_DOC_CONVERSION_FAILED",
                )

        converted = output_path.read_bytes()
        if not converted:
            raise LegacyDocConversionError(
                "旧版 .doc 自动转换失败：转换结果为空",
                code="LEGACY_DOC_CONVERSION_EMPTY",
            )
        return converted
