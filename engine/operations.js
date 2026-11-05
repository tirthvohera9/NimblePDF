import { PdfCapabilityError, PdfEngineError } from "./errors.js";

/** @typedef {{type:"delete"|"move"|"rotate"|"extract", page:number, to?:number, degrees?:90|180|270}} PageOperation */

/** @param {PageOperation[]} operations @param {number|null} pageCount */
export function planPageOperations(operations, pageCount) {
  if (!Array.isArray(operations)) throw new PdfEngineError("Operations must be an array.", "INVALID_OPERATIONS");
  const simulatedCount = pageCount ?? Number.POSITIVE_INFINITY;
  const plan = operations.map((operation, index) => {
    if (!operation || !["delete", "move", "rotate", "extract"].includes(operation.type)) {
      throw new PdfEngineError(`Invalid operation at index ${index}.`, "INVALID_OPERATION", { index });
    }
    if (!Number.isInteger(operation.page) || operation.page < 1 || operation.page > simulatedCount) {
      throw new PdfEngineError(`Page must be a valid 1-based page number at index ${index}.`, "INVALID_PAGE", { index });
    }
    if (operation.type === "move" && (!Number.isInteger(operation.to) || operation.to < 1 || operation.to > simulatedCount)) {
      throw new PdfEngineError(`Move target must be a valid page number at index ${index}.`, "INVALID_PAGE", { index });
    }
    if (operation.type === "rotate" && ![90, 180, 270].includes(operation.degrees)) {
      throw new PdfEngineError(`Rotation must be 90, 180, or 270 degrees at index ${index}.`, "INVALID_ROTATION", { index });
    }
    return Object.freeze({ ...operation });
  });
  return Object.freeze({ pageCount, operations: Object.freeze(plan), executable: false, reason: "Planning only: PDF object graph rewriting is not implemented." });
}

/** @param {string} capability */
export function requireCapability(capability) {
  throw new PdfCapabilityError(capability);
}

