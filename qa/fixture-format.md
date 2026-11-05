# QA fixture format

Fixtures are JSON objects representing a local PDF job. They are test inputs,
not PDFs and must not contain secrets or real customer data.

```json
{
  "id": "smoke-basic",
  "input": {
    "path": "fixtures/sample.pdf",
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "bytes": 1048576,
    "pages": 2
  },
  "health": {
    "expectedStatus": "warning",
    "minimumFindings": 1,
    "requiredSeverities": ["warning"]
  },
  "workflow": {
    "goal": "compress and validate",
    "maxSteps": 8,
    "maxBytes": 104857600
  },
  "ui": {
    "contractVersion": "1",
    "requiredActions": ["health", "plan", "run"]
  }
}
```

## Rules

* `id`, `input.path`, and `workflow.goal` are required non-empty strings.
* `input.path` is relative, uses `/`, and must not contain `..`, a drive letter,
  or a URL scheme. `bytes` and `pages` are non-negative integers.
* `sha256` is exactly 64 lowercase hexadecimal characters.
* `health.minimumFindings` is an integer from 0 through 100.
* `workflow.maxSteps` is 1 through 50 and `maxBytes` is positive.
* Unknown top-level keys should fail validation so the fixture cannot silently
  drift from the contract.
* Use a second fixture with `input.bytes` above the product limit to prove the
  safety rejection path. Never use a real external URL as a fixture.

