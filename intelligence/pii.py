"""Conservative, explainable PII pattern detection."""

from dataclasses import dataclass
import re
from typing import List, Pattern, Tuple

from .models import clamp_confidence


@dataclass(frozen=True)
class PiiFinding:
    kind: str
    value: str
    start: int
    end: int
    confidence: float
    masked_value: str


_PATTERNS: Tuple[Tuple[str, Pattern[str], float], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), 0.98),
    ("phone", re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\w)"), 0.9),
    ("ssn", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"), 0.97),
    ("credit_card", re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)"), 0.82),
)


def _mask(value: str, kind: str) -> str:
    if kind == "email" and "@" in value:
        local, domain = value.split("@", 1)
        return "*" * len(local) + "@" + domain
    visible = value[-4:] if len(value) >= 4 else ""
    return "*" * max(0, len(value) - len(visible)) + visible


def detect_pii(text: str) -> List[PiiFinding]:
    """Find likely PII while returning masked values for safer downstream use."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    findings: List[PiiFinding] = []
    for kind, pattern, confidence in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if kind == "credit_card" and not _passes_luhn(re.sub(r"[ -]", "", value)):
                continue
            findings.append(PiiFinding(kind, value, match.start(), match.end(),
                                       clamp_confidence(confidence), _mask(value, kind)))
    return sorted(findings, key=lambda finding: (finding.start, finding.end))


def _passes_luhn(number: str) -> bool:
    if not 13 <= len(number) <= 19 or not number.isdigit():
        return False
    total = sum((digit if index % 2 == 0 else (digit * 2 - 9 if digit * 2 > 9 else digit * 2))
                for index, digit in enumerate(map(int, reversed(number))))
    return total % 10 == 0
