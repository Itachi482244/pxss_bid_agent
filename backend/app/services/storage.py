from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse

from minio import Minio

from app.core.config import settings


def _minio_endpoint() -> tuple[str, bool]:
    endpoint = settings.minio_endpoint
    if "://" not in endpoint:
        return endpoint, False
    parsed = urlparse(endpoint)
    return parsed.netloc, parsed.scheme == "https"


def get_minio_client() -> Minio:
    endpoint, secure = _minio_endpoint()
    return Minio(
        endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=secure,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object_bytes(
    *,
    bucket: str,
    object_key: str,
    data: bytes,
    content_type: str | None,
) -> None:
    client = get_minio_client()
    ensure_bucket(client, bucket)
    client.put_object(
        bucket,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )


def get_object_bytes(*, bucket: str, object_key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
