"""Verified local PDF operations used by the loopback API."""

from __future__ import annotations

import base64
import hashlib
import io
from typing import Iterable

from pypdf import PdfReader, PdfWriter


class PdfOperationError(ValueError):
    """A user-correctable PDF operation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _reader(data: bytes) -> PdfReader:
    if not data.startswith(b"%PDF-"):
        raise PdfOperationError("INVALID_PDF", "Input does not have a PDF signature.")
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise PdfOperationError("ENCRYPTED_PDF", "Encrypted PDFs are not supported without a password.")
        return reader
    except PdfOperationError:
        raise
    except Exception as exc:
        raise PdfOperationError("INVALID_PDF", f"Could not parse PDF: {exc}") from exc


def _write(writer: PdfWriter) -> bytes:
    output = io.BytesIO()
    writer.write(output)
    result = output.getvalue()
    if not result.startswith(b"%PDF-"):
        raise PdfOperationError("WRITE_FAILED", "The local PDF engine did not produce a valid PDF.")
    _reader(result)
    return result


def merge(documents: Iterable[bytes]) -> bytes:
    writer = PdfWriter()
    count = 0
    for data in documents:
        reader = _reader(data)
        for page in reader.pages:
            writer.add_page(page)
            count += 1
    if count == 0:
        raise PdfOperationError("EMPTY_INPUT", "At least one page is required.")
    return _write(writer)


def transform(data: bytes, operation: str, pages: list[int] | None = None, degrees: int = 90) -> bytes:
    reader = _reader(data)
    total = len(reader.pages)
    selected = pages if pages is not None else list(range(1, total + 1))
    if not selected:
        raise PdfOperationError("EMPTY_PAGES", "Select at least one page.")
    if any(not isinstance(page, int) or page < 1 or page > total for page in selected):
        raise PdfOperationError("INVALID_PAGE", f"Pages must be between 1 and {total}.")
    if operation == "split":
        writer = PdfWriter()
        for page_number in selected:
            writer.add_page(reader.pages[page_number - 1])
        return _write(writer)
    if operation == "rotate":
        if degrees not in (90, 180, 270):
            raise PdfOperationError("INVALID_ROTATION", "Rotation must be 90, 180, or 270 degrees.")
        writer = PdfWriter()
        selected_set = set(selected)
        for number, page in enumerate(reader.pages, start=1):
            if number in selected_set:
                page.rotate(degrees)
            writer.add_page(page)
        return _write(writer)
    raise PdfOperationError("UNSUPPORTED_OPERATION", f"Operation '{operation}' is not executable.")


def analyze(data: bytes) -> dict:
    reader = _reader(data)
    text_by_page = []
    for page in reader.pages:
        try:
            text_by_page.append((page.extract_text() or "").strip())
        except Exception:
            text_by_page.append("")
    metadata = reader.metadata or {}
    tagged = bool(reader.root_object.get("/MarkInfo"))
    has_title = bool(metadata.get("/Title"))
    has_language = bool(reader.root_object.get("/Lang"))
    return {
        "pageCount": len(reader.pages),
        "textPages": sum(bool(text) for text in text_by_page),
        "textCharacters": sum(len(text) for text in text_by_page),
        "pages": [{"page": index, "characters": len(text), "preview": text[:240]} for index, text in enumerate(text_by_page, 1)],
        "accessibility": {
            "score": sum((has_title, has_language, tagged)) * 33 + (1 if len(reader.pages) else 0),
            "checks": [
                {"id": "title", "pass": has_title, "message": "Document title metadata is present." if has_title else "Add a document title."},
                {"id": "language", "pass": has_language, "message": "Document language is declared." if has_language else "Declare the document language."},
                {"id": "tags", "pass": tagged, "message": "Tagged structure is present." if tagged else "Tagged structure was not detected."},
                {"id": "text", "pass": bool(sum(bool(text) for text in text_by_page)), "message": "Text is available on at least one page." if any(text_by_page) else "No extractable text; OCR may be needed."},
            ],
        },
    }


def sanitize_metadata(data: bytes) -> bytes:
    reader = _reader(data)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})
    return _write(writer)


def result(data: bytes, name: str) -> dict:
    reader = _reader(data)
    return {
        "name": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pageCount": len(reader.pages),
        "data": base64.b64encode(data).decode("ascii"),
    }
