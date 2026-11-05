"""Checks for redaction plans; this module does not modify PDF content."""

from dataclasses import dataclass
from typing import Iterable

from .errors import RedactionSafetyError


@dataclass(frozen=True, order=True)
class RedactionRange:
    start: int
    end: int
    replacement: str = "[REDACTED]"


def check_redaction_plan(text: str, ranges: Iterable[RedactionRange]) -> tuple[RedactionRange, ...]:
    """Validate text ranges before a caller performs a real content rewrite."""
    if not isinstance(text, str):
        raise RedactionSafetyError("source text must be a string")
    plan = tuple(ranges)
    if not plan:
        raise RedactionSafetyError("at least one redaction range is required")
    previous_end = -1
    for item in sorted(plan):
        if item.start < 0 or item.end <= item.start or item.end > len(text):
            raise RedactionSafetyError("redaction range is outside source text")
        if item.start < previous_end:
            raise RedactionSafetyError("redaction ranges overlap")
        if not item.replacement or item.replacement == text[item.start:item.end]:
            raise RedactionSafetyError("redaction must replace content with different text")
        previous_end = item.end
    return tuple(sorted(plan))
