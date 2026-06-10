"""OCR 能力：图片 → 文本 + 表格。

厂商无关抽象（``OcrClient``）+ 阿里云读光 OCR 适配器（``ocr-api20210707`` 的
``RecognizeAdvanced``，高精度全文识别 + 表格还原，直传二进制无需 OSS）。

上层（PDF 逐页渲染、历史文件萃取）只依赖 ``OcrClient`` 协议与 ``OcrResult``，
更换/新增供应商时不影响调用方。SDK 为惰性导入，未安装/未配置时应用仍可启动。
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ocr")

ALIYUN_PROVIDER = "aliyun-ocr-api20210707"


class OcrError(Exception):
    """OCR 调用失败的基类异常。"""

    code = "OCR_FAILED"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class OcrNotConfiguredError(OcrError):
    code = "OCR_NOT_CONFIGURED"


@dataclass(frozen=True)
class OcrTable:
    """识别出的单个表格，按行列还原成二维文本。"""

    rows: list[list[str]]

    def to_text(self) -> str:
        rendered = [" | ".join(cell.strip() for cell in row if cell.strip()) for row in self.rows]
        return "\n".join(line for line in rendered if line).strip()


@dataclass(frozen=True)
class OcrResult:
    """OCR 识别结果（厂商无关）。"""

    text: str
    tables: list[OcrTable] = field(default_factory=list)
    confidence: float | None = None
    provider: str = ""
    raw: dict[str, Any] | None = None


@runtime_checkable
class OcrClient(Protocol):
    provider: str

    def recognize_image(self, image_bytes: bytes) -> OcrResult:
        """识别单张图片的二进制，返回文本与表格。"""
        ...


def _reconstruct_table(table: dict[str, Any]) -> OcrTable:
    """从读光 OCR 的 ``cellInfos`` 还原表格二维结构。

    每个 cell 含 ``xsc``（起始列）/``ysc``（起始行）/``word``；合并单元格只在起始格放字。
    """

    cells = table.get("cellInfos") or table.get("cellInfo") or []
    if not cells:
        return OcrTable(rows=[])

    def _int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    n_rows = _int(table.get("yCellSize"), 0)
    n_cols = _int(table.get("xCellSize"), 0)
    for cell in cells:
        n_rows = max(n_rows, _int(cell.get("yec"), _int(cell.get("ysc"))) + 1)
        n_cols = max(n_cols, _int(cell.get("xec"), _int(cell.get("xsc"))) + 1)

    if n_rows <= 0 or n_cols <= 0:
        return OcrTable(rows=[])

    grid = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    for cell in cells:
        row = _int(cell.get("ysc"))
        col = _int(cell.get("xsc"))
        word = str(cell.get("word") or "").strip()
        if 0 <= row < n_rows and 0 <= col < n_cols and word:
            existing = grid[row][col]
            grid[row][col] = f"{existing} {word}".strip() if existing else word
    return OcrTable(rows=grid)


def _average_confidence(words: list[dict[str, Any]]) -> float | None:
    probs: list[float] = []
    for word in words:
        prob = word.get("prob")
        if prob is None:
            continue
        try:
            probs.append(float(prob))
        except (TypeError, ValueError):
            continue
    if not probs:
        return None
    avg = sum(probs) / len(probs)
    # 读光 OCR 的 prob 取值约 0-100，归一化到 0-1。
    return round(avg / 100 if avg > 1 else avg, 4)


def parse_recognize_advanced_data(data: dict[str, Any]) -> OcrResult:
    """把 RecognizeAdvanced 的 ``data`` JSON 解析为厂商无关结果（纯函数，可单测）。"""

    text = str(data.get("content") or "").strip()
    tables = [
        ocr_table
        for table in (data.get("prism_tablesInfo") or [])
        if (ocr_table := _reconstruct_table(table)).rows
    ]
    confidence = _average_confidence(data.get("prism_wordsInfo") or [])
    return OcrResult(
        text=text,
        tables=tables,
        confidence=confidence,
        provider=ALIYUN_PROVIDER,
        raw=data,
    )


class AliyunOcrClient:
    """阿里云读光 OCR 适配器（``RecognizeAdvanced``，直传二进制）。"""

    provider = ALIYUN_PROVIDER

    def __init__(
        self,
        *,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        try:
            from alibabacloud_ocr_api20210707.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:  # pragma: no cover - 依赖未安装时的兜底
            raise OcrNotConfiguredError(
                "缺少阿里云 OCR SDK，请安装 alibabacloud-ocr-api20210707"
            ) from exc

        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint,
        )
        self._client = Client(config)
        self._timeout_ms = int(timeout_seconds * 1000)

    def recognize_image(self, image_bytes: bytes) -> OcrResult:
        from alibabacloud_ocr_api20210707 import models as ocr_models
        from alibabacloud_tea_util import models as util_models

        request = ocr_models.RecognizeAdvancedRequest(
            body=io.BytesIO(image_bytes),
            output_table=True,
            need_rotate=True,
        )
        runtime = util_models.RuntimeOptions(
            read_timeout=self._timeout_ms,
            connect_timeout=self._timeout_ms,
        )
        try:
            response = self._client.recognize_advanced_with_options(request, runtime)
        except Exception as exc:  # noqa: BLE001 - 统一包装为 OcrError 向上抛
            message = getattr(exc, "message", None) or str(exc)
            logger.warning("aliyun_ocr_call_failed", error=message)
            raise OcrError(f"阿里云 OCR 调用失败：{message}") from exc

        raw_data = getattr(getattr(response, "body", None), "data", None)
        if raw_data is None:
            raise OcrError("阿里云 OCR 返回为空")
        try:
            data = json.loads(raw_data) if isinstance(raw_data, str) else dict(raw_data)
        except (TypeError, ValueError) as exc:
            raise OcrError("阿里云 OCR 返回无法解析为 JSON") from exc
        return parse_recognize_advanced_data(data)


def get_ocr_client() -> OcrClient:
    """按配置返回 OCR 客户端；未启用或缺凭证时抛 ``OcrNotConfiguredError``。"""

    if not settings.aliyun_ocr_enabled:
        raise OcrNotConfiguredError("OCR 未启用（设置 ALIYUN_OCR_ENABLED=true 开启）")
    if not (settings.aliyun_ocr_access_key_id and settings.aliyun_ocr_access_key_secret):
        raise OcrNotConfiguredError("阿里云 OCR AccessKey 未配置")
    return AliyunOcrClient(
        access_key_id=settings.aliyun_ocr_access_key_id,
        access_key_secret=settings.aliyun_ocr_access_key_secret,
        endpoint=settings.aliyun_ocr_endpoint,
        timeout_seconds=settings.aliyun_ocr_timeout_seconds,
    )
