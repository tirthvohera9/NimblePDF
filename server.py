"""Dependency-light local development server and JSON contract."""

from __future__ import annotations

import json
import base64
import hashlib
import mimetypes
import ntpath
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from intelligence import parse_workflow_intent, recommend_pdf_health
from security.files import FileLimits
from pdf_ops import PdfOperationError, analyze, merge, result, sanitize_metadata, transform

ROOT = Path(__file__).resolve().parent
MAX_BYTES = FileLimits().max_bytes
MAX_REQUEST_BYTES = 70 * 1024 * 1024
MAX_GOAL_LENGTH = 500
MAX_OPERATION_BYTES = 50 * 1024 * 1024
MAX_ANALYZE_BYTES = 20 * 1024 * 1024


def api_error(code: str, message: str) -> dict:
    """Return a stable, safe error shape while retaining the legacy message."""
    return {"error": message, "code": code, "message": message}


def health_payload() -> dict:
    report = recommend_pdf_health({
        "page_count": 1,
        "file_size_bytes": 1,
        "has_text": True,
        "has_metadata": True,
    }).to_dict()
    findings = report["findings"] or [{
        "code": "LOCAL_READY",
        "severity": "info",
        "message": "Local processing is ready.",
        "recommendation": "Drop in a PDF to inspect it.",
        "confidence": 1.0,
    }]
    status = "ok" if report["score"] >= 80 else "warning" if report["score"] > 0 else "error"
    return {
        "status": status,
        "score": report["score"],
        "version": "0.1.0",
        "limits": {"maxBytes": MAX_BYTES},
        "findings": [
            {
                "id": item["code"],
                "severity": item["severity"],
                "message": item["message"],
                "recommendation": item.get("recommendation", ""),
            }
            for item in findings
        ],
    }


def plan_payload(body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        return 400, api_error("INVALID_BODY", "Request body must be a JSON object.")
    input_data = body.get("input")
    if not isinstance(input_data, dict):
        return 400, api_error("INVALID_INPUT", "input must be an object.")
    path = input_data.get("path")
    if not isinstance(path, str) or not path.strip():
        return 400, api_error("INVALID_PATH", "input.path must be a non-empty local PDF path.")
    path = path.strip()
    path_parts = re.split(r"[/\\]", path)
    if (
        "\x00" in path
        or any(part == ".." for part in path_parts)
        or Path(path).is_absolute()
        or ntpath.isabs(path)
        or path.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", path)
        or "://" in path
    ):
        return 400, api_error("INVALID_PATH", "Input path must remain local and traversal-free.")
    if not path.lower().endswith(".pdf"):
        return 400, api_error("INVALID_PATH", "input.path must reference a PDF file.")
    raw_size = input_data.get("bytes", 0)
    if isinstance(raw_size, bool) or not isinstance(raw_size, int):
        return 400, api_error("INVALID_SIZE", "input.bytes must be a non-negative integer.")
    size = raw_size
    if size < 0:
        return 400, api_error("INVALID_SIZE", "input.bytes must be a non-negative integer.")
    if size > MAX_BYTES:
        return 413, api_error("FILE_TOO_LARGE", f"Input exceeds the {MAX_BYTES} byte local limit.")
    raw_max_steps = body.get("maxSteps", 8)
    if isinstance(raw_max_steps, bool) or not isinstance(raw_max_steps, int):
        return 400, api_error("INVALID_MAX_STEPS", "maxSteps must be an integer between 1 and 50.")
    max_steps = raw_max_steps
    if not 1 <= max_steps <= 50:
        return 400, api_error("INVALID_MAX_STEPS", "maxSteps must be between 1 and 50.")
    goal = body.get("goal", "")
    if not isinstance(goal, str):
        return 400, api_error("INVALID_GOAL", "goal must be a string.")
    if len(goal) > MAX_GOAL_LENGTH:
        return 400, api_error("INVALID_GOAL", f"goal must be at most {MAX_GOAL_LENGTH} characters.")
    intent = parse_workflow_intent(goal)
    action = intent.action if intent.action != "unknown" else "inspect"
    steps = [
        {
            "id": "inspect",
            "label": "Inspect PDF structure",
            "estimate": 0.1,
            "input": "local PDF path",
            "output": "PDF metadata and health findings",
        },
        {
            "id": action,
            "label": action.capitalize(),
            "estimate": 0.2,
            "input": "inspected PDF",
            "output": "local workflow plan",
        },
    ]
    if action == "inspect":
        steps = steps[:1]
    else:
        steps = steps[:max_steps]
    return 200, {
        "intent": intent.to_dict(),
        "input": {"path": path, "bytes": size},
        "steps": steps,
        "totalEstimate": round(sum(step["estimate"] for step in steps), 2),
        "executable": False,
        "note": "Planning is separate from execution. Use /api/operate for verified merge, split, rotate, or sanitization.",
    }


def operation_payload(body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        return 400, api_error("INVALID_BODY", "Request body must be a JSON object.")
    operation = body.get("operation")
    if operation not in {"merge", "split", "rotate", "sanitize-metadata"}:
        return 400, api_error("UNSUPPORTED_OPERATION", "operation must be merge, split, rotate, or sanitize-metadata.")
    raw_files = body.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        return 400, api_error("INVALID_FILES", "files must be a non-empty array.")
    documents: list[tuple[str, bytes]] = []
    total_bytes = 0
    try:
        for item in raw_files:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("data"), str):
                return 400, api_error("INVALID_FILE", "Each file requires a name and base64 data.")
            name = item["name"].strip()
            data = base64.b64decode(item["data"], validate=True)
            total_bytes += len(data)
            if not name.lower().endswith(".pdf"):
                return 400, api_error("INVALID_FILE", "Only PDF files are supported.")
            documents.append((name, data))
    except (ValueError, base64.binascii.Error):
        return 400, api_error("INVALID_FILE", "File data must be valid base64.")
    if total_bytes > MAX_OPERATION_BYTES:
        return 413, api_error("FILE_TOO_LARGE", "Combined operation input exceeds the 50 MB local limit.")
    try:
        if operation == "merge":
            output = merge(data for _, data in documents)
            output_name = "nimblepdf-merged.pdf"
        elif operation == "sanitize-metadata":
            output = sanitize_metadata(documents[0][1])
            output_name = "nimblepdf-sanitized.pdf"
        else:
            pages = body.get("pages")
            if not isinstance(pages, list) or any(isinstance(page, bool) or not isinstance(page, int) for page in pages):
                return 400, api_error("INVALID_PAGES", "pages must be an array of page numbers.")
            output = transform(documents[0][1], operation, pages, body.get("degrees", 90))
            output_name = f"nimblepdf-{operation}.pdf"
        return 200, {"operation": operation, "verified": True, "output": result(output, output_name)}
    except PdfOperationError as exc:
        return 422, api_error(exc.code, str(exc))


def analyze_payload(body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict) or not isinstance(body.get("name"), str) or not isinstance(body.get("data"), str):
        return 400, api_error("INVALID_FILE", "name and base64 data are required.")
    try:
        data = base64.b64decode(body["data"], validate=True)
    except (ValueError, base64.binascii.Error):
        return 400, api_error("INVALID_FILE", "File data must be valid base64.")
    if len(data) > MAX_ANALYZE_BYTES:
        return 413, api_error("FILE_TOO_LARGE", "Analysis input exceeds the 20 MB local limit.")
    try:
        return 200, {"name": body["name"], "sha256": hashlib.sha256(data).hexdigest(), "analysis": analyze(data)}
    except PdfOperationError as exc:
        return 422, api_error(exc.code, str(exc))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: object, content_type: str = "application/json") -> None:
        data = payload if isinstance(payload, bytes) else (
            json.dumps(payload).encode("utf-8") if content_type == "application/json" else str(payload).encode("utf-8")
        )
        self.send_response(status)
        if content_type == "application/json":
            content_type = "application/json; charset=utf-8"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-src blob:; object-src blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._send(200, health_payload())
        if path == "/api/ui-contract":
            return self._send(200, {
                "version": "0.1.0",
                "actions": [
                    {"name": "health", "method": "GET", "path": "/api/health"},
                    {"name": "plan", "method": "POST", "path": "/api/plan"},
                    {"name": "run", "method": "POST", "path": "/api/run"},
                    {"name": "operate", "method": "POST", "path": "/api/operate"},
                    {"name": "analyze", "method": "POST", "path": "/api/analyze"},
                ],
                "states": ["loading", "error", "success"],
                "plan": {
                    "request": {"input": "object", "goal": "string", "maxSteps": "integer"},
                    "response": {"intent": "object", "steps": "array", "totalEstimate": "number"},
                },
                "operate": {
                    "request": {"operation": "merge|split|rotate|sanitize-metadata", "files": "base64 PDF array", "pages": "integer array"},
                    "response": {"verified": "boolean", "output": "base64 PDF with sha256"},
                },
                "analyze": {
                    "request": {"name": "string", "data": "base64 PDF"},
                    "response": {"analysis": "text and accessibility checks"},
                },
            })
        if path in ("/", "/index.html"):
            path = "/app/index.html"
        elif path.startswith("/engine/"):
            file_path = (ROOT / "engine" / path.removeprefix("/engine/")).resolve()
            if ROOT not in file_path.parents or not file_path.is_file():
                return self._send(404, {"error": "Not found"})
            return self._send(200, file_path.read_bytes(), mimetypes.guess_type(file_path.name)[0] or "application/javascript")
        elif not path.startswith("/app/"):
            return self._send(404, {"error": "Not found"})
        file_path = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in file_path.parents or not file_path.is_file():
            return self._send(404, {"error": "Not found"})
        self._send(200, file_path.read_bytes(), mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path not in ("/api/plan", "/api/run", "/api/operate", "/api/analyze"):
            return self._send(404, {"error": "Not found"})
        try:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                return self._send(411, api_error("LENGTH_REQUIRED", "Content-Length is required."))
            length = int(raw_length)
            if length < 0 or length > MAX_REQUEST_BYTES:
                return self._send(413, api_error("REQUEST_TOO_LARGE", "Request body is too large."))
            if "application/json" not in self.headers.get_content_type().lower():
                return self._send(415, api_error("UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json."))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if urlparse(self.path).path == "/api/analyze":
                status, payload = analyze_payload(body)
                return self._send(status, payload)
            if urlparse(self.path).path == "/api/operate":
                status, payload = operation_payload(body)
                return self._send(status, payload)
            status, payload = plan_payload(body)
            if urlparse(self.path).path == "/api/run":
                if status != 200:
                    return self._send(status, payload)
                return self._send(409, api_error("EXECUTION_UNAVAILABLE", "Use /api/operate for the verified local PDF operations."))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            status, payload = 400, api_error("INVALID_JSON", "Request body must contain valid UTF-8 JSON.")
        self._send(status, payload)

    def log_message(self, *_args: object) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 3000), Handler)
    print("NimblePDF running at http://127.0.0.1:3000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
