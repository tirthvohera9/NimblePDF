"""Local page thumbnail generation through Poppler."""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

from pdf_ops import PdfOperationError, _reader

PDFTOPPM = shutil.which("pdftoppm") or r"C:\Users\tirth\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftoppm.exe"


def thumbnails(data: bytes, limit: int = 12) -> list[dict]:
    reader = _reader(data)
    if not Path(PDFTOPPM).is_file():
        raise PdfOperationError("RENDER_ENGINE_UNAVAILABLE", "Install Poppler before generating page thumbnails.")
    with tempfile.TemporaryDirectory(prefix="nimblepdf-preview-") as directory:
        source = Path(directory) / "source.pdf"
        source.write_bytes(data)
        prefix = Path(directory) / "page"
        completed = subprocess.run(
            [PDFTOPPM, "-png", "-scale-to", "360", "-f", "1", "-l", str(min(len(reader.pages), limit)), str(source), str(prefix)],
            capture_output=True, text=True, timeout=120,
        )
        if completed.returncode:
            raise PdfOperationError("RENDER_FAILED", completed.stderr.strip() or "Could not render PDF pages.")
        return [
            {"page": index, "data": base64.b64encode(path.read_bytes()).decode("ascii"), "mime": "image/png"}
            for index, path in enumerate(sorted(Path(directory).glob("page-*.png")), 1)
        ]
