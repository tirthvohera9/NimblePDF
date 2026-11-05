# NimblePDF local engine

Dependency-light, browser-native PDF inspection primitives. The engine uses
`Uint8Array`, `ArrayBuffer`, `Blob`, and standard text encoders only; it has no
runtime or package dependencies.

```js
import { inspect, planPageOperations } from "./index.js";

const report = await inspect(fileOrArrayBuffer);
console.log(report.metadata, report.health);

const plan = planPageOperations([{ type: "rotate", page: 1, degrees: 90 }],
  report.metadata.pageCount);
```

## Scope and guarantees

`inspect` deterministically reports signature/version, byte and object counts,
best-effort page count, cross-reference markers, linearization, encryption,
JavaScript, and AcroForm markers. `analyzeHealth` turns those facts into
structured findings. `planPageOperations` validates and freezes a page
operation plan, but does not mutate PDF bytes.

Object-graph parsing, rendering, text extraction, and rewriting are
intentionally unavailable. Calling `parse`, `render`, or `rewrite` throws a
`PdfCapabilityError` with a stable capability code. This makes unsupported
features explicit rather than silently corrupting files.

Pure functions can be tested without browser APIs by passing `Uint8Array`
values to `analyzeMetadata`, `analyzeHealth`, and `planPageOperations`.

