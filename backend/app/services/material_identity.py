from __future__ import annotations

import json
import re
from typing import Any, Mapping

from app.models import EnterpriseMaterial


def _fingerprint_text(value: object) -> str:
    text = str(value or "").strip().lower()
    return "".join(re.findall(r"[0-9a-z\u4e00-\u9fff]+", text))


def _structured_fingerprint(value: object) -> str:
    if not value:
        return ""
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    return _fingerprint_text(text)


def material_identity_key_from_values(
    *,
    material_type: object,
    name: object,
    issuing_authority: object = None,
    certificate_no: object = None,
    holder_name: object = None,
    project_name: object = None,
    amount: object = None,
    structured_fields: object = None,
    evidence_text: object = None,
) -> str:
    type_key = _fingerprint_text(material_type) or "unknown"
    cert_key = _fingerprint_text(certificate_no)
    if cert_key:
        return f"{type_key}:cert:{cert_key}"

    parts = [
        _fingerprint_text(name),
        _fingerprint_text(issuing_authority),
        _fingerprint_text(holder_name),
        _fingerprint_text(project_name),
        _fingerprint_text(amount),
        _structured_fingerprint(structured_fields),
        _fingerprint_text(evidence_text),
    ]
    body = ":".join(part for part in parts if part)
    return f"{type_key}:content:{body}" if body else f"{type_key}:empty"


def enterprise_material_identity_key(material: EnterpriseMaterial) -> str:
    return material_identity_key_from_values(
        material_type=material.material_type,
        name=material.name,
        issuing_authority=material.issuing_authority,
        certificate_no=material.certificate_no,
        holder_name=material.holder_name,
        project_name=material.project_name,
        amount=material.amount,
        structured_fields=material.structured_fields,
        evidence_text=material.evidence_text,
    )


def material_snapshot_identity_key(snapshot: Mapping[str, Any] | None) -> str:
    snapshot = snapshot or {}
    return material_identity_key_from_values(
        material_type=snapshot.get("material_type"),
        name=snapshot.get("name") or snapshot.get("material_name"),
        issuing_authority=snapshot.get("issuing_authority"),
        certificate_no=snapshot.get("certificate_no"),
        holder_name=snapshot.get("holder_name"),
        project_name=snapshot.get("project_name"),
        amount=snapshot.get("amount"),
        structured_fields=snapshot.get("structured_fields"),
        evidence_text=snapshot.get("evidence_text"),
    )
