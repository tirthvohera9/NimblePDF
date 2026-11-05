import { PdfEngineError } from "./errors.js";

/** @typedef {{level:"info"|"warning"|"error", code:string, message:string}} HealthFinding */

/** @param {import("./metadata.js").PdfMetadata} metadata */
export function analyzeHealth(metadata) {
  if (!metadata || typeof metadata !== "object") throw new PdfEngineError("Metadata is required.", "INVALID_METADATA");
  /** @type {HealthFinding[]} */
  const findings = [];
  if (!metadata.validSignature) findings.push({ level: "error", code: "INVALID_SIGNATURE", message: "The file does not begin with a PDF signature." });
  if (metadata.byteLength === 0) findings.push({ level: "error", code: "EMPTY_FILE", message: "The file is empty." });
  if (!metadata.hasStartXref) findings.push({ level: "warning", code: "MISSING_STARTXREF", message: "No startxref marker was found; structural parsing may fail." });
  if (!metadata.hasCrossReference) findings.push({ level: "warning", code: "MISSING_XREF", message: "No cross-reference table or stream was found." });
  if (metadata.isEncrypted) findings.push({ level: "info", code: "ENCRYPTED", message: "The document declares encryption; content operations require credentials and a full parser." });
  if (metadata.hasJavaScript) findings.push({ level: "warning", code: "JAVASCRIPT", message: "The document contains JavaScript markers; treat it as active content." });
  if (metadata.pageCount === null) findings.push({ level: "warning", code: "UNKNOWN_PAGE_COUNT", message: "Page count could not be determined without full parsing." });
  return { ok: !findings.some((item) => item.level === "error"), findings };
}

