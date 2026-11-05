"""Deterministic workflow intent parsing from natural-language requests."""

from dataclasses import dataclass, field
import re
from typing import Dict, List

from .models import clamp_confidence


_ACTIONS = (
    ("merge", ("merge", "combine", "join")),
    ("split", ("split", "separate", "extract pages")),
    ("compress", ("compress", "reduce size", "shrink")),
    ("convert", ("convert", "export", "save as")),
    ("redact", ("redact", "hide", "remove sensitive")),
    ("summarize", ("summarize", "summary", "key points")),
    ("extract", ("extract text", "extract data", "read")),
)
_FORMATS = ("pdf", "docx", "word", "png", "jpg", "jpeg", "text", "csv")


@dataclass(frozen=True)
class WorkflowIntent:
    action: str
    entities: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.0
    needs_clarification: bool = True
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "entities": self.entities,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "rationale": self.rationale,
        }


def parse_workflow_intent(text: str) -> WorkflowIntent:
    """Parse common PDF workflow requests without network or model calls."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return WorkflowIntent("unknown", confidence=0.0, rationale="No request supplied.")

    matches = [
        (action, phrase)
        for action, phrases in _ACTIONS
        for phrase in phrases
        if phrase in normalized
    ]
    action = matches[0][0] if matches else "unknown"
    entities: Dict[str, List[str]] = {}
    formats = sorted({fmt for fmt in _FORMATS if re.search(r"\b" + re.escape(fmt) + r"\b", normalized)})
    if formats:
        entities["formats"] = formats
    pages = re.search(r"\b(?:pages?|page range)\s+([\d,\-\s]+)", normalized)
    if pages:
        entities["pages"] = [re.sub(r"\s+", "", pages.group(1)).strip(",")]
    confidence = 0.0 if action == "unknown" else 0.65
    if len(matches) == 1:
        confidence += 0.15
    if formats:
        confidence += 0.1
    confidence = clamp_confidence(confidence)
    return WorkflowIntent(
        action=action,
        entities=entities,
        confidence=confidence,
        needs_clarification=action == "unknown" or confidence < 0.7,
        rationale=("Matched explicit local keyword rules." if action != "unknown"
                   else "No supported workflow action matched."),
    )
