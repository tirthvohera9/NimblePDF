"""Local-first privacy and security helpers for NimblePDF."""

from .errors import (
    FilenameSecurityError,
    FileValidationError,
    MetadataPolicyError,
    RedactionSafetyError,
    SecurityError,
)
from .files import FileLimits, FileValidator, ValidationResult, safe_filename
from .metadata import MetadataPolicy, sanitize_metadata
from .redaction import RedactionRange, check_redaction_plan

__all__ = [
    "FileLimits",
    "FileValidator",
    "FilenameSecurityError",
    "FileValidationError",
    "MetadataPolicy",
    "MetadataPolicyError",
    "RedactionRange",
    "RedactionSafetyError",
    "SecurityError",
    "ValidationResult",
    "check_redaction_plan",
    "safe_filename",
    "sanitize_metadata",
]
