"""Structured extraction interfaces with no PDF parser dependency."""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Protocol

from .models import clamp_confidence


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ExtractionResult:
    pages: List[PageText] = field(default_factory=list)
    fields: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pages": [page.__dict__ for page in self.pages],
            "fields": self.fields,
            "warnings": self.warnings,
        }


class DocumentExtractor(Protocol):
    """Adapter contract for an optional local PDF/text extraction engine."""

    def extract(self, source: Any) -> ExtractionResult:
        ...


class TextDocumentExtractor:
    """Reference extractor for already-decoded page text."""

    def extract(self, source: Iterable[str]) -> ExtractionResult:
        pages = [PageText(i, text, clamp_confidence(1.0 if text.strip() else 0.0))
                 for i, text in enumerate(source, 1)]
        return ExtractionResult(pages=pages)
