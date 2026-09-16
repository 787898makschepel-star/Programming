"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.formatError = exports.getPlatform = void 0;
const os_1 = __importDefault(require("os"));
const keychain_js_1 = require("../common/keychain.js");
const mongodb_redact_1 = require("mongodb-redact");
const getPlatform = () => {
    switch (os_1.default.platform()) {
        case "win32":
            return "windows";
        case "darwin":
            return "mac";
        case "linux":
            return "linux";
        default:
            return null;
    }
};
exports.getPlatform = getPlatform;
const formatError = (error) => {
    const message = error instanceof Error ? error.message : String(error);
    return (0, mongodb_redact_1.redact)(message, keychain_js_1.Keychain.root.allSecrets);
};
exports.formatError = formatError;
//# sourceMappingURL=setupAiToolsUtils.js.map