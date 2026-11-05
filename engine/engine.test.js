import test from "node:test";
import assert from "node:assert/strict";
import { analyzeMetadata, analyzeHealth, planPageOperations, PdfCapabilityError } from "./index.js";

test("metadata analysis is deterministic", () => {
  const bytes = new TextEncoder().encode("%PDF-1.7\n1 0 obj\n<< /Type /Page >>\nendobj\nxref\nstartxref");
  assert.deepEqual(analyzeMetadata(bytes), {
    validSignature: true, version: "1.7", byteLength: bytes.length, objectCount: 1,
    pageCount: 1, hasCrossReference: true, hasStartXref: true, isLinearized: false,
    isEncrypted: false, hasJavaScript: false, hasAcroForm: false,
  });
});

test("health reports malformed input", () => {
  const result = analyzeHealth(analyzeMetadata(new Uint8Array()));
  assert.equal(result.ok, false);
  assert.ok(result.findings.some((finding) => finding.code === "INVALID_SIGNATURE"));
});

test("operation planning validates and freezes", () => {
  const plan = planPageOperations([{ type: "rotate", page: 1, degrees: 90 }], 2);
  assert.equal(plan.executable, false);
  assert.ok(Object.isFrozen(plan.operations));
  assert.throws(() => planPageOperations([{ type: "rotate", page: 1, degrees: 45 }], 2), { code: "INVALID_ROTATION" });
});

test("unsupported capabilities are explicit", async () => {
  const { parse } = await import("./index.js");
  assert.throws(parse, PdfCapabilityError);
});

