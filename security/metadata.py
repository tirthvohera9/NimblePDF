"""Privacy-oriented metadata filtering."""

from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import MetadataPolicyError

DEFAULT_PRIVATE_KEYS = frozenset({
    "author", "creator", "producer", "subject", "title", "keywords",
    "creationdate", "moddate", "xmp", "gps", "location",
})


@dataclass(frozen=True)
class MetadataPolicy:
    """Policy for metadata exported with a local document."""

    remove_keys: frozenset[str] = field(default_factory=lambda: DEFAULT_PRIVATE_KEYS)
    allowed_keys: frozenset[str] = frozenset()
    max_value_length: int = 1024
    reject_non_string_values: bool = False


def sanitize_metadata(metadata: Mapping[str, Any], policy: MetadataPolicy = MetadataPolicy()) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise MetadataPolicyError("metadata must be a mapping")
    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key.strip():
            raise MetadataPolicyError("metadata keys must be non-empty strings")
        normalized = key.casefold()
        if normalized in policy.remove_keys or (
            policy.allowed_keys and key not in policy.allowed_keys
        ):
            continue
        if policy.reject_non_string_values and not isinstance(value, str):
            raise MetadataPolicyError(f"non-string metadata value rejected: {key}")
        if isinstance(value, str) and len(value) > policy.max_value_length:
            raise MetadataPolicyError(f"metadata value is too long: {key}")
        result[key] = value
    return result
