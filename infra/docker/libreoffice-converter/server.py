"""Minimal headless LibreOffice .doc -> .docx HTTP converter.

Stdlib-only sidecar so the (natively-run) backend can convert legacy binary
Word files over HTTP, mirroring how it already talks to the Infinity sidecar.

Endpoints:
  GET  /health            -> 200 "ok"
  POST /convert           -> request body is the raw .doc bytes; responds with
                             the converted .docx bytes (200) or a JSON error.
                             The original filename may be supplied via the
                             ``X-Filename`` header or ``?filename=`` query.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_BODY_BYTES = int(os.environ.get("CONVERTER_MAX_BODY_BYTES", str(200 * 1024 * 1024)))
CONVERT_TIMEOUT_SECONDS = float(os.environ.get("CONVERTER_TIMEOUT_SECONDS", "120"))
PORT = int(os.environ.get("PORT", "2004"))


def _find_soffice() -> str | None:
    configured = os.environ.get("SOFFICE_PATH", "").strip()
    if configured:
        return configured
    return shutil.which("soffice") or shutil.which("libreoffice")


def _summarize(value: str) -> str:
    return " ".join(value.split())[:600]


class ConversionError(Exception):
    def __init__(self, message: str, *, status: int = 502, code: str = "CONVERSION_FAILED") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def convert(data: bytes, *, filename: str) -> bytes:
    soffice = _find_soffice()
    if soffice is None:
        raise ConversionError("soffice/libreoffice not found in image", status=503, code="CONVERTER_UNAVAILABLE")

    safe_stem = Path(filename or "source.doc").stem or "source"
    with tempfile.TemporaryDirectory(prefix="lo-convert-") as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / f"{safe_stem}.doc"
        output_dir = tmp_dir / "out"
        profile_dir = tmp_dir / "lo-profile"
        output_dir.mkdir()
        profile_dir.mkdir()
        input_path.write_bytes(data)

        command = [
            soffice,
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
                timeout=CONVERT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionError("conversion timed out", status=504, code="CONVERSION_TIMEOUT") from exc

        output_path = output_dir / f"{safe_stem}.docx"
        if completed.returncode != 0 or not output_path.exists():
            candidates = sorted(output_dir.glob("*.docx"))
            if completed.returncode == 0 and candidates:
                output_path = candidates[0]
            else:
                detail = _summarize(completed.stderr) or _summarize(completed.stdout) or "no .docx produced"
                raise ConversionError(f"soffice failed: {detail}", status=502, code="CONVERSION_FAILED")

        converted = output_path.read_bytes()
        if not converted:
            raise ConversionError("conversion produced empty output", status=502, code="CONVERSION_EMPTY")
        return converted


class Handler(BaseHTTPRequestHandler):
    server_version = "lo-converter/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not found", "code": "NOT_FOUND"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/convert":
            self._send_json(404, {"error": "not found", "code": "NOT_FOUND"})
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            self._send_json(400, {"error": "empty request body", "code": "EMPTY_BODY"})
            return
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request body too large", "code": "BODY_TOO_LARGE"})
            return

        filename = self.headers.get("X-Filename", "").strip()
        if not filename:
            query = parse_qs(parsed.query)
            filename = (query.get("filename", [""])[0] or "").strip()
        data = self.rfile.read(length)

        try:
            converted = convert(data, filename=filename or "source.doc")
        except ConversionError as exc:
            self._send_json(exc.status, {"error": str(exc), "code": exc.code})
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": _summarize(str(exc)), "code": "INTERNAL_ERROR"})
            return

        self.send_response(200)
        self.send_header("Content-Type", DOCX_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(converted)))
        self.end_headers()
        self.wfile.write(converted)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A002
        # Keep container logs quiet but still surface conversion failures.
        return


def main() -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"libreoffice-converter listening on :{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
