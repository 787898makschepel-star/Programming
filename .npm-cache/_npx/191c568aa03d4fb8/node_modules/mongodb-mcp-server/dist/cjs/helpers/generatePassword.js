"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateSecurePassword = generateSecurePassword;
const crypto_1 = require("crypto");
const util_1 = require("util");
const randomBytesAsync = (0, util_1.promisify)(crypto_1.randomBytes);
async function generateSecurePassword() {
    const buf = await randomBytesAsync(16);
    const pass = buf.toString("base64url");
    return pass;
}
//# sourceMappingURL=generatePassword.js.map