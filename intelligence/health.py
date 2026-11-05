"""Deterministic PDF health checks based on supplied metadata."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

from .models import clamp_confidence


@dataclass(frozen=True)
class HealthFinding:
    code: str
    severity: str
    message: str
    recommendation: str
    confidence: float = 1.0


@dataclass(frozen=True)
class PdfHealthReport:
    findings: List[HealthFinding] = field(default_factory=list)
    score: int = 100

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "findings": [finding.__dict__ for finding in self.findings],
        }


def recommend_pdf_health(metadata: Mapping[str, Any]) -> PdfHealthReport:
    """Return safe recommendations; this function never mutates or opens files.

    Supported metadata keys include ``page_count``, ``file_size_bytes``,
    ``has_text``, ``has_metadata``, ``is_encrypted``, and ``has_embedded_files``.
    """
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    findings: List[HealthFinding] = []
    def add(code: str, severity: str, message: str, recommendation: str, confidence: float = 1.0) -> None:
        findings.append(HealthFinding(code, severity, message, recommendation, clamp_confidence(confidence)))

    pages = metadata.get("page_count")
    if isinstance(pages, int) and pages <= 0:
        add("no-pages", "error", "The document reports no pages.", "Verify the PDF was generated correctly.")
    size = metadata.get("file_size_bytes")
    if isinstance(size, (int, float)) and size > 25 * 1024 * 1024:
        add("large-file", "warning", "The PDF is larger than 25 MiB.", "Consider image downsampling or lossless stream compression.")
    if metadata.get("has_text") is False:
        add("no-text", "warning", "No text layer was detected.", "Run OCR locally if the document is a scanned image.")
    if metadata.get("has_metadata") is False:
        add("missing-metadata", "info", "Document metadata is missing.", "Add title, author, and subject metadata before sharing.")
    if metadata.get("is_encrypted") is True:
        add("encrypted", "info", "The document is encrypted.", "Confirm recipients have access and record the password separately.")
    if metadata.get("has_embedded_files") is True:
        add("embedded-files", "warning", "The PDF contains embedded files.", "Review embedded content before opening or distributing it.")
    deductions = sum({"error": 25, "warning": 12, "info": 3}[f.severity] for f in findings)
    return PdfHealthReport(findings=findings, score=max(0, 100 - deductions))
