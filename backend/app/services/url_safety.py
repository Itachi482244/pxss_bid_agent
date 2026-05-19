from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse, urlunparse


ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443, None}
BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}


@dataclass(frozen=True)
class UrlValidationResult:
    is_allowed: bool
    normalized_url: str | None
    blocked_reason: str | None


def _is_blocked_ip(hostname: str) -> bool:
    try:
        parsed = ip_address(hostname)
    except ValueError:
        return False
    return (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def validate_public_file_url(raw_url: str) -> UrlValidationResult:
    url = raw_url.strip()
    if not url:
        return UrlValidationResult(False, None, "URL 不能为空")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return UrlValidationResult(False, None, "仅支持 http 或 https 链接")
    if not parsed.hostname:
        return UrlValidationResult(False, None, "URL 缺少主机名")
    if parsed.username or parsed.password:
        return UrlValidationResult(False, None, "URL 不允许携带用户名或密码")
    if parsed.port not in ALLOWED_PORTS:
        return UrlValidationResult(False, None, "URL 端口不在允许范围内")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local"):
        return UrlValidationResult(False, None, "URL 指向本地主机或本地域名")
    if _is_blocked_ip(hostname):
        return UrlValidationResult(False, None, "URL 指向内网、回环或保留地址")

    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            "",
            parsed.query,
            "",
        )
    )
    return UrlValidationResult(True, normalized, None)
