/** @typedef {Uint8Array | ArrayBuffer | Blob} BinaryInput */

/** @param {BinaryInput} input */
export async function toBytes(input) {
  if (input instanceof Uint8Array) return new Uint8Array(input);
  if (input instanceof ArrayBuffer) return new Uint8Array(input.slice(0));
  if (typeof Blob !== "undefined" && input instanceof Blob) return new Uint8Array(await input.arrayBuffer());
  throw new TypeError("Expected a Uint8Array, ArrayBuffer, or Blob.");
}

/** @param {Uint8Array} bytes @param {number} offset @param {number} length */
export function decodeAscii(bytes, offset = 0, length = bytes.length - offset) {
  return new TextDecoder("latin1").decode(bytes.subarray(offset, offset + length));
}

/** @param {Uint8Array} bytes */
export function findAscii(bytes, text) {
  const needle = new TextEncoder().encode(text);
  outer: for (let i = 0; i <= bytes.length - needle.length; i += 1) {
    for (let j = 0; j < needle.length; j += 1) if (bytes[i + j] !== needle[j]) continue outer;
    return i;
  }
  return -1;
}

/** @param {Uint8Array} bytes */
export function countAscii(bytes, text) {
  const needle = new TextEncoder().encode(text);
  let count = 0;
  for (let i = 0; i <= bytes.length - needle.length; i += 1) {
    let match = true;
    for (let j = 0; j < needle.length; j += 1) match &&= bytes[i + j] === needle[j];
    if (match) count += 1;
  }
  return count;
}

