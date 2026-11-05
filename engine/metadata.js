import { decodeAscii, findAscii, countAscii } from "./bytes.js";

/** @typedef {{validSignature:boolean, version:string|null, byteLength:number, objectCount:number, pageCount:number|null, hasCrossReference:boolean, hasStartXref:boolean, isLinearized:boolean, isEncrypted:boolean, hasJavaScript:boolean, hasAcroForm:boolean}} PdfMetadata */

/** @param {Uint8Array} bytes */
export function analyzeMetadata(bytes) {
  const head = decodeAscii(bytes, 0, Math.min(bytes.length, 1024));
  const text = decodeAscii(bytes);
  const versionMatch = head.match(/^%PDF-(\d\.\d)/);
  const pageMatches = [...text.matchAll(/\/Type\s*\/Page(?:\s|\/|>|$)/g)];
  return {
    validSignature: head.startsWith("%PDF-"),
    version: versionMatch ? versionMatch[1] : null,
    byteLength: bytes.byteLength,
    objectCount: (text.match(/\b\d+\s+\d+\s+obj\b/g) || []).length,
    pageCount: pageMatches.length || null,
    hasCrossReference: /\bxref\b/.test(text) || countAscii(bytes, "/XRef") > 0,
    hasStartXref: findAscii(bytes, "startxref") >= 0,
    isLinearized: /\/Linearized\b/.test(head),
    isEncrypted: /\/Encrypt\b/.test(text),
    hasJavaScript: /\/(?:JavaScript|JS)\b/.test(text),
    hasAcroForm: /\/AcroForm\b/.test(text),
  };
}

