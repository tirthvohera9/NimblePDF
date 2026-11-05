# NimblePDF

NimblePDF is a lightweight, local-first PDF workflow assistant. It is designed
to explain what a document needs before asking the user to run a workflow.
The MVP has no external API, account, upload, or package dependency.

## Run

From the project directory:

```powershell
python .\server.py
```

Open <http://127.0.0.1:3000>. The browser UI and JSON endpoints are served from
the loopback interface only.

## Current MVP

- Local PDF drop zone and job queue
- Browser-side PDF signature/structure inspection
- Local SHA-256 fingerprints and duplicate-content detection
- Downloadable evidence receipts containing metadata, findings, and privacy attestations
- Deterministic health findings
- Local workflow intent parsing and plan preview API
- File validation and redaction-safety contracts
- QA smoke-test and acceptance checklist

The engine intentionally reports unsupported PDF rewriting explicitly instead
of pretending that a visual overlay is secure redaction. Merge, split, OCR, and

## Netlify deployment

The repository includes a Netlify build configuration. Connect the repository
to Netlify with `netlify.toml` as the build configuration; every push to the
configured production branch will rebuild and publish the static app
automatically. The build copies the browser app and local engine into `dist`
so the deployed asset paths match the source layout. Merge, split, OCR, and
redaction are not enabled until a verified local PDF object engine is available.
