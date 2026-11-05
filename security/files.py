"""Local file and filename validation with no external dependencies."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Optional, Union

from .errors import FilenameSecurityError, FileValidationError

PathLike = Union[str, Path]
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]")
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename(name: str, *, fallback: str = "document", max_length: int = 120) -> str:
    """Return a conservative basename suitable for local output files.

    Directory components, control characters, and shell-sensitive punctuation are
    removed. This does not create or overwrite a file.
    """
    if max_length < 1:
        raise FilenameSecurityError("max_length must be positive")
    if not isinstance(fallback, str) or not fallback.strip():
        raise FilenameSecurityError("fallback must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        name = fallback
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL_CHARS.sub("", name)
    name = _SAFE_CHARS.sub("_", name).strip(" .")
    if not name:
        name = fallback
    stem = name.split(".", 1)[0].upper()
    if stem in _RESERVED_NAMES:
        name = "_" + name
    name = name[:max_length].rstrip(" .")
    if not name:
        raise FilenameSecurityError("filename becomes empty after sanitization")
    return name


@dataclass(frozen=True)
class FileLimits:
    max_bytes: int = 50 * 1024 * 1024
    allowed_extensions: frozenset[str] = frozenset({".pdf"})
    allowed_mime_types: frozenset[str] = frozenset({"application/pdf"})
    require_pdf_signature: bool = True


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    size_bytes: int
    extension: str
    mime_type: Optional[str]


@dataclass
class FileValidator:
    limits: FileLimits = field(default_factory=FileLimits)

    def validate(self, path: PathLike) -> ValidationResult:
        candidate = Path(path)
        if not candidate.is_file():
            raise FileValidationError("path must identify a regular local file")
        if candidate.is_symlink():
            raise FileValidationError("symbolic links are not accepted")
        try:
            size = candidate.stat().st_size
        except OSError as exc:
            raise FileValidationError("cannot inspect file") from exc
        if size > self.limits.max_bytes:
            raise FileValidationError("file exceeds configured size limit")
        extension = candidate.suffix.lower()
        if extension not in self.limits.allowed_extensions:
            raise FileValidationError(f"extension is not allowed: {extension or '<none>'}")
        try:
            with candidate.open("rb") as stream:
                signature = stream.read(5)
        except OSError as exc:
            raise FileValidationError("cannot read file signature") from exc
        mime = "application/pdf" if signature == b"%PDF-" else None
        if self.limits.require_pdf_signature and extension == ".pdf" and mime is None:
            raise FileValidationError("file does not have a valid PDF signature")
        if self.limits.allowed_mime_types and mime not in self.limits.allowed_mime_types:
            raise FileValidationError("file type is not allowed")
        return ValidationResult(candidate, size, extension, mime)
