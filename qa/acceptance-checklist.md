# NimblePDF acceptance checklist

Run `.\qa\smoke-test.ps1 -BaseUrl http://127.0.0.1:3000` after starting the
local app. Attach the command output or request/response evidence to each item.

## Local-only operation

- [ ] App binds only to loopback; a non-loopback `BaseUrl` is rejected by the
      smoke script.
- [ ] Health, plan, and run requests complete without internet access (disable
      network and repeat).
- [ ] No telemetry, remote font, CDN, or cloud-storage request is made.
- [ ] Redirects and URLs reported by the app remain `localhost`, `127.0.0.1`,
      or `::1`.

## Health findings

- [ ] `GET /api/health` returns HTTP 200 and `status` is `ok`, `warning`, or
      `error`.
- [ ] `score` is numeric and between 0 and 100.
- [ ] At least one finding has stable `id`, valid `severity`, and actionable
      `message`; the same fixture produces the same IDs twice.

## Workflow planning

- [ ] Planning the same fixture twice returns the same ordered step IDs.
- [ ] Every step has an ID, human-readable label, and declared input/output.
- [ ] The plan reports a positive estimate and never exceeds `maxSteps`.
- [ ] A plan is shown before execution; execution cannot start with an invalid
      or missing local input.

## Safety limits

- [ ] A file above the configured byte limit is rejected before processing.
- [ ] `../outside.pdf`, an absolute path, and `https://example.test/a.pdf` are
      rejected as inputs.
- [ ] A hung request is cancelled within the documented timeout; the UI exits
      loading state and shows an error.
- [ ] No source PDF is overwritten by default; output is a separate path.

## UI integration contract

- [ ] `GET /api/ui-contract` exposes a version and `health`, `plan`, and `run`
      actions with method/path and request/response shapes.
- [ ] The UI exposes loading, error, and success states for each action.
- [ ] Health findings render severity and message without relying on
      positional array order.
- [ ] Plan steps render in server-provided order and the run action is disabled
      while planning or running.
- [ ] API validation errors include a stable code and user-safe message; no
      local path, token, or stack trace is shown to the user.
