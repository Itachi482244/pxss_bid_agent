from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class ModelConfigCryptoError(Exception):
    pass


def mask_api_key(value: str) -> str:
    key = value.strip()
    if not key:
        return ""
    if len(key) <= 8:
        return f"{key[:2]}****{key[-2:]}"
    return f"{key[:4]}****{key[-4:]}"


def _load_key() -> bytes:
    raw = settings.model_config_encryption_key.strip()
    if not raw:
        raise ModelConfigCryptoError("MODEL_CONFIG_ENCRYPTION_KEY is not configured")
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise ModelConfigCryptoError("MODEL_CONFIG_ENCRYPTION_KEY must be base64 encoded") from exc
    if len(key) != 32:
        raise ModelConfigCryptoError("MODEL_CONFIG_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def encrypt_api_key(value: str) -> tuple[str, str, str]:
    plaintext = value.strip()
    if not plaintext:
        raise ModelConfigCryptoError("API key cannot be empty")
    key = _load_key()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    encrypted = "aesgcm:" + base64.b64encode(nonce + ciphertext).decode("ascii")
    return encrypted, mask_api_key(plaintext), settings.model_config_encryption_key_version


def decrypt_api_key(value: str) -> str:
    if not value:
        return ""
    if not value.startswith("aesgcm:"):
        raise ModelConfigCryptoError("Unsupported API key ciphertext format")
    key = _load_key()
    try:
        payload = base64.b64decode(value.split(":", 1)[1])
        nonce, ciphertext = payload[:12], payload[12:]
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise ModelConfigCryptoError("Failed to decrypt API key") from exc
    return plaintext.decode("utf-8")
