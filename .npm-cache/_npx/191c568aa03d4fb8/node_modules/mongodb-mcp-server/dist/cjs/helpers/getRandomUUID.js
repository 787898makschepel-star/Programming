"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRandomUUID = getRandomUUID;
const bson_1 = require("bson");
/**
 * Generates a random UUID that works in both Node.js and browser environments.
 * Attempts to use Node.js crypto first, then falls back to Web Crypto API.
 */
function getRandomUUID() {
    try {
        // Try Node.js crypto module first
        // Using require to avoid import errors in browser environments
        // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/consistent-type-imports
        const nodeCrypto = require("crypto");
        return nodeCrypto.randomUUID();
    }
    catch {
        // Fall back to Web Crypto API (available in browsers and modern Node.js)
        if (typeof globalThis !== "undefined" &&
            globalThis.crypto &&
            typeof globalThis.crypto.randomUUID === "function") {
            return globalThis.crypto.randomUUID();
        }
        // If neither is available, use the BSON UUID
        return new bson_1.UUID().toString();
    }
}
//# sourceMappingURL=getRandomUUID.js.map