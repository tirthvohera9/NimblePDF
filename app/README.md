# NimblePDF app shell

A dependency-light, local-first PDF workspace prototype built with plain HTML, CSS, and vanilla JavaScript.

## Run locally

From this directory, open `index.html` in a browser. For a local server (recommended):

```bash
python -m http.server 8080
```

Then visit [http://localhost:8080](http://localhost:8080).

## Included

- Responsive dashboard layout with PDF drop zone and file picker
- Local-only inspection queue with metadata and per-file health findings
- Health summary derived from inspected files (not a placeholder status)
- Verified local merge, split, and rotate downloads through the loopback server
- Loading, success, error, empty, and unavailable-action states
- Keyboard-accessible upload area and responsive mobile layout
- No build step, dependencies, uploads, or external runtime services
