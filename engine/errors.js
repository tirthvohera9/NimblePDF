/**
 * Errors exposed by the local PDF engine.
 */
export class PdfEngineError extends Error {
  /** @param {string} message @param {string} code @param {Record<string, unknown>} [details] */
  constructor(message, code, details = {}) {
    super(message);
    this.name = "PdfEngineError";
    this.code = code;
    this.details = details;
  }
}

export class PdfCapabilityError extends PdfEngineError {
  /** @param {string} capability @param {string} [message] */
  constructor(capability, message = `Capability "${capability}" is not available in the dependency-light engine.`) {
    super(message, "CAPABILITY_UNAVAILABLE", { capability });
    this.name = "PdfCapabilityError";
    this.capability = capability;
  }
}

