"""Shared, JSON-serialisable data contracts."""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict


def to_dict(value: Any) -> Any:
    """Convert intelligence results into plain JSON-friendly values."""
    if is_dataclass(value):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    return value


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 3)))


def validate_confidence(value: float) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return clamp_confidence(value)
