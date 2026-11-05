# NimblePDF MVP QA strategy

This directory is the executable, dependency-free QA gate for the MVP. It tests
observable contracts rather than implementation details.

## Test levels

| Level | Command/input | Pass signal |
|---|---|---|
| Fixture/schema | `.\qa\smoke-test.ps1 -ValidateFixture <fixture.json>` | Fixture is valid and contains only allowed local paths |
| Contract smoke | `.\qa\smoke-test.ps1 -BaseUrl http://127.0.0.1:3000` | All required HTTP responses, limits, and UI metadata pass |
| Manual acceptance | `qa/acceptance-checklist.md` | Every checkbox has evidence (screenshot, request, or log) |

The script uses only PowerShell/.NET built-ins. It never uploads a document,
calls a non-loopback host, or requires package installation. Run it against a
locally started NimblePDF process. The default endpoint names are documented in
the checklist; override them when the implementation uses different paths.

## Required measurable MVP behavior

* **Local-only:** the configured base URL resolves to `localhost`, `127.0.0.1`,
  or `::1`; redirects and every reported request URL must remain loopback.
* **Health findings:** the health response has a stable status, numeric score,
  and non-empty findings with `id`, `severity`, and `message`.
* **Workflow planning:** a plan is deterministic for the same fixture,
  contains ordered steps, and reports a positive total estimate.
* **Safety limits:** oversized input is rejected before processing; traversal
  paths and non-local URLs are rejected; request timeout is bounded.
* **UI integration:** the app exposes a machine-readable contract describing
  health, plan, and run actions, plus loading/error/success states.

Record command output and the app version/commit with each run. A failed
assertion is a release blocker until dispositioned.
