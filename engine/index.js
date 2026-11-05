import { toBytes } from "./bytes.js";
import { analyzeMetadata } from "./metadata.js";
import { analyzeHealth } from "./health.js";
import { planPageOperations, requireCapability } from "./operations.js";
export { PdfEngineError, PdfCapabilityError } from "./errors.js";
export { analyzeMetadata } from "./metadata.js";
export { analyzeHealth } from "./health.js";
export { planPageOperations } from "./operations.js";
export { toBytes } from "./bytes.js";

export const ENGINE_VERSION = "0.1.0";

/** @param {import("./bytes.js").BinaryInput} input */
export async function inspect(input) {
  const bytes = await toBytes(input);
  const metadata = analyzeMetadata(bytes);
  return Object.freeze({ engineVersion: ENGINE_VERSION, metadata, health: analyzeHealth(metadata) });
}

export const capabilities = Object.freeze({
  inspect: true,
  healthAnalysis: true,
  pageOperationPlanning: true,
  parseObjects: false,
  rewritePdf: false,
  renderPages: false,
  extractText: false,
});

export function parse() { return requireCapability("parseObjects"); }
export function render() { return requireCapability("renderPages"); }
export function rewrite() { return requireCapability("rewritePdf"); }

