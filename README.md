# NimblePDF

NimblePDF is a local-first PDF change desk: inspect documents, fingerprint
them, plan a workflow, and execute verified page operations without uploads or
paid APIs.

## Run

From the project directory:

```powershell
python .\server.py
```

Open <http://127.0.0.1:3000>. The browser UI and JSON endpoints are served from
the loopback interface only.

## Included

- Local PDF drop zone and job queue
- Browser-side PDF signature/structure inspection
- Local SHA-256 fingerprints and duplicate-content detection
- Downloadable evidence receipts containing metadata, findings, and privacy attestations
- Verified local merge, split, and rotate operations through the loopback server
- Verified metadata sanitization, local text analysis, accessibility preflight, and browser previews
- Deterministic health findings
- Local workflow intent parsing and plan preview API
- File validation and redaction-safety contracts
- QA smoke-test and acceptance checklist

The engine intentionally reports unsupported capabilities explicitly instead of
pretending that a visual overlay is secure redaction. OCR and secure content
redaction remain gated because this machine has no OCR/raster engine; metadata
sanitization is available and verified.

## Limits

The local server accepts PDFs up to 50 MB. Originals stay in the browser tab;
operation payloads are sent only to the loopback server at `127.0.0.1`.

## Packaging

Run `.\package.ps1` once, then launch `.\run-nimblepdf.bat`. No account,
external API, or cloud upload is required.
