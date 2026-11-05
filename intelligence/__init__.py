"""Local-first document intelligence for NimblePDF.

The package intentionally uses only the Python standard library.  It exposes
small, deterministic building blocks that can be composed by a PDF workflow.
"""

from .extraction import DocumentExtractor, ExtractionResult, PageText, TextDocumentExtractor
from .health import HealthFinding, PdfHealthReport, recommend_pdf_health
from .intent import WorkflowIntent, parse_workflow_intent
from .pii import PiiFinding, detect_pii

__all__ = [
    "DocumentExtractor",
    "ExtractionResult",
    "PageText",
    "TextDocumentExtractor",
    "HealthFinding",
    "PdfHealthReport",
    "recommend_pdf_health",
    "WorkflowIntent",
    "parse_workflow_intent",
    "PiiFinding",
    "detect_pii",
]
