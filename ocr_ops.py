"""Local OCR and irreversible raster redaction using Tesseract and Poppler."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter

from pdf_ops import PdfOperationError, _reader, _write

TESSERACT = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PDFTOPPM = shutil.which("pdftoppm") or r"C:\Users\tirth\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftoppm.exe"


def _require_tools() -> None:
    if not Path(TESSERACT).is_file() or not PDFTOPPM:
        raise PdfOperationError("OCR_ENGINE_UNAVAILABLE", "Install Tesseract and Poppler before using OCR or redaction.")


def _pages(data: bytes, directory: str) -> list[Path]:
    _require_tools()
    source = Path(directory) / "source.pdf"
    source.write_bytes(data)
    prefix = Path(directory) / "page"
    completed = subprocess.run(
        [PDFTOPPM, "-png", "-r", "150", str(source), str(prefix)],
        capture_output=True, text=True, timeout=120,
    )
    if completed.returncode:
        raise PdfOperationError("RASTERIZE_FAILED", completed.stderr.strip() or "Could not rasterize PDF pages.")
    return sorted(Path(directory).glob("page-*.png"))


def _ocr_text(image: Path) -> str:
    completed = subprocess.run(
        [TESSERACT, str(image), "stdout", "--psm", "3"],
        capture_output=True, text=True, timeout=120,
    )
    if completed.returncode:
        raise PdfOperationError("OCR_FAILED", completed.stderr.strip() or "Tesseract could not read the page.")
    return completed.stdout.strip()


def ocr_pdf(data: bytes) -> bytes:
    _reader(data)
    with tempfile.TemporaryDirectory(prefix="nimblepdf-ocr-") as directory:
        pages = _pages(data, directory)
        if not pages:
            raise PdfOperationError("OCR_FAILED", "No pages were rendered for OCR.")
        writer = PdfWriter()
        for image in pages:
            pdf_bytes = subprocess.run(
                [TESSERACT, str(image), "stdout", "--dpi", "150", "pdf"],
                capture_output=True, timeout=120,
            )
            if pdf_bytes.returncode:
                raise PdfOperationError("OCR_FAILED", pdf_bytes.stderr.decode(errors="replace").strip())
            page = PdfReader(io.BytesIO(pdf_bytes.stdout)).pages[0]
            writer.add_page(page)
        writer.add_metadata({})
        return _write(writer)


def redact_terms(data: bytes, terms: list[str]) -> bytes:
    _reader(data)
    normalized = [term.strip() for term in terms if isinstance(term, str) and term.strip()]
    if not normalized:
        raise PdfOperationError("INVALID_REDACTION_TERMS", "Provide at least one non-empty term.")
    with tempfile.TemporaryDirectory(prefix="nimblepdf-redact-") as directory:
        pages = _pages(data, directory)
        rendered: list[Image.Image] = []
        found: set[str] = set()
        for image_path in pages:
            image = Image.open(image_path).convert("RGB")
            tsv = subprocess.run(
                [TESSERACT, str(image_path), "stdout", "--psm", "3", "tsv"],
                capture_output=True, text=True, timeout=120,
            )
            if tsv.returncode:
                raise PdfOperationError("OCR_FAILED", tsv.stderr.strip())
            draw = ImageDraw.Draw(image)
            rows: list[list[str]] = []
            for line in tsv.stdout.splitlines()[1:]:
                fields = line.split("\t")
                if len(fields) < 12:
                    continue
                word = fields[11].strip()
                if not word:
                    continue
                rows.append(fields)
            groups: dict[tuple[str, ...], list[list[str]]] = {}
            for fields in rows:
                key = tuple(fields[index] for index in (1, 2, 3, 4))
                groups.setdefault(key, []).append(fields)
            for fields_list in groups.values():
                line_text = " ".join(fields[11] for fields in fields_list)
                compact_line = re.sub(r"\s+", "", line_text).casefold()
                for term in normalized:
                    compact_term = re.sub(r"\s+", "", term).casefold()
                    if compact_term in compact_line:
                        try:
                            boxes = [tuple(int(fields[index]) for index in (6, 7, 8, 9)) for fields in fields_list]
                            left = min(box[0] for box in boxes)
                            top = min(box[1] for box in boxes)
                            right = max(box[0] + box[2] for box in boxes)
                            bottom = max(box[1] + box[3] for box in boxes)
                        except ValueError:
                            continue
                        draw.rectangle((left, top, right, bottom), fill="black")
                        found.add(term)
            rendered.append(image)
        missing = [term for term in normalized if term not in found]
        if missing:
            raise PdfOperationError("REDACTION_TERM_NOT_FOUND", f"Could not locate: {', '.join(missing)}")
        output = io.BytesIO()
        rendered[0].save(output, format="PDF", save_all=True, append_images=rendered[1:], resolution=150)
        result = output.getvalue()
        reader = _reader(result)
        extracted = "\n".join((page.extract_text() or "") for page in reader.pages).casefold()
        if any(term.casefold() in extracted for term in normalized):
            raise PdfOperationError("REDACTION_VERIFY_FAILED", "Sensitive text remained extractable after redaction.")
        return result
