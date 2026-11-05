"""Explicit exceptions raised by security helpers."""


class SecurityError(ValueError):
    """Base class for expected security-policy violations."""


class FilenameSecurityError(SecurityError):
    """A filename cannot be made safe under the configured policy."""


class FileValidationError(SecurityError):
    """A file does not satisfy size, type, or location limits."""


class MetadataPolicyError(SecurityError):
    """Metadata violates the configured privacy policy."""


class RedactionSafetyError(SecurityError):
    """A redaction plan is incomplete or unsafe to apply."""
