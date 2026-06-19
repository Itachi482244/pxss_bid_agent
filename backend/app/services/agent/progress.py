from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from sqlalchemy.orm import Session


DEFAULT_DISPLAY_MAX_STRING_CHARS = 2000
DEFAULT_DISPLAY_MAX_LIST_ITEMS = 25

DEFAULT_PROTECTED_DISPLAY_KEYS = {
    "id",
    "ids",
    "object_id",
    "project_id",
    "section_id",
    "task_id",
    "run_key",
    "compliance_item_id",
    "enterprise_material_id",
    "qualification_evaluation_id",
    "qualification_decision_id",
    "source_document_id",
    "source_version_id",
    "source_chunk_id",
    "source_page_no",
    "source_ref_json",
    "enterprise_material_chunk_id",
    "chunk_index",
    "query_hash",
    "sha256",
    "certificate_no",
    "evidence_text",
    "source_quote",
    "matched_material_id",
}


def _is_protected_key(key: str | None, protected_keys: set[str]) -> bool:
    if key is None:
        return False
    return key in protected_keys or key.endswith("_id") or key.endswith("_ids")


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars].rstrip()}...（已截断 {omitted} 字）"


def budget_display_payload(
    value: Any,
    *,
    max_string_chars: int = DEFAULT_DISPLAY_MAX_STRING_CHARS,
    max_list_items: int = DEFAULT_DISPLAY_MAX_LIST_ITEMS,
    protected_keys: Iterable[str] = DEFAULT_PROTECTED_DISPLAY_KEYS,
    _key: str | None = None,
) -> Any:
    """Trim display-oriented JSON while preserving authoritative references.

    This function is intentionally conservative: ids, source references, hashes,
    and evidence text are preserved because accept handlers may still need them.
    The budget is for previews/explanations, not for business identifiers.
    """

    protected = set(protected_keys)
    if isinstance(value, dict):
        return {
            key: budget_display_payload(
                item,
                max_string_chars=max_string_chars,
                max_list_items=max_list_items,
                protected_keys=protected,
                _key=str(key),
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        items = [
            budget_display_payload(
                item,
                max_string_chars=max_string_chars,
                max_list_items=max_list_items,
                protected_keys=protected,
                _key=_key,
            )
            for item in value[:max_list_items]
        ]
        if len(value) > max_list_items:
            items.append({"_truncated": True, "omitted_count": len(value) - max_list_items})
        return items
    if isinstance(value, str) and not _is_protected_key(_key, protected):
        return _truncate_text(value, max_string_chars)
    return value


@dataclass(frozen=True)
class ProgressSnapshot:
    percent: int
    step: str | None
    activity: str
    current: int | None = None
    total: int | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "percent": self.percent,
            "step": self.step,
            "activity": self.activity,
            "updated_at": self.updated_at or datetime.now(UTC).isoformat(),
        }
        if self.current is not None:
            payload["current"] = self.current
        if self.total is not None:
            payload["total"] = self.total
        return payload


class ProgressReporter:
    def __init__(self, db: Session, task: Any) -> None:
        self.db = db
        self.task = task
        self._last_snapshot = ProgressSnapshot(
            percent=int(task.progress or 0),
            step=None,
            activity="等待开始",
        ).as_dict()

    @property
    def snapshot(self) -> dict[str, Any]:
        return dict(self._last_snapshot)

    def report(
        self,
        *,
        percent: int,
        step: str | None,
        activity: str,
        current: int | None = None,
        total: int | None = None,
        commit: bool = False,
    ) -> dict[str, Any]:
        bounded_percent = max(0, min(100, int(percent)))
        progress = ProgressSnapshot(
            percent=bounded_percent,
            step=step,
            activity=activity,
            current=current,
            total=total,
            updated_at=datetime.now(UTC).isoformat(),
        ).as_dict()
        output_json = dict(self.task.output_json or {})
        output_json["progress"] = progress
        self.task.progress = bounded_percent
        self.task.output_json = output_json
        self._last_snapshot = progress
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return progress

