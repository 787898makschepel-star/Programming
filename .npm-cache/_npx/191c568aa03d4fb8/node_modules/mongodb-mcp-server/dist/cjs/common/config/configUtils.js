"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getLocalDataPath = getLocalDataPath;
exports.getLogPath = getLogPath;
exports.getExportsPath = getExportsPath;
exports.commaSeparatedToArray = commaSeparatedToArray;
exports.parseBoolean = parseBoolean;
exports.oneWayOverride = oneWayOverride;
exports.onlyLowerThanBaseValueOverride = onlyLowerThanBaseValueOverride;
exports.onlyStricterLogLevelOverride = onlyStricterLogLevelOverride;
exports.onlySubsetOfBaseValueOverride = onlySubsetOfBaseValueOverride;
const path_1 = __importDefault(require("path"));
const os_1 = __importDefault(require("os"));
function getLocalDataPath() {
    return process.platform === "win32"
        ? path_1.default.join(process.env.LOCALAPPDATA || process.env.APPDATA || os_1.default.homedir(), "mongodb")
        : path_1.default.join(os_1.default.homedir(), ".mongodb");
}
function getLogPath() {
    const logPath = path_1.default.join(getLocalDataPath(), "mongodb-mcp", ".app-logs");
    return logPath;
}
function getExportsPath() {
    return path_1.default.join(getLocalDataPath(), "mongodb-mcp", "exports");
}
function commaSeparatedToArray(str) {
    if (str === undefined) {
        return undefined;
    }
    if (typeof str === "string") {
        return str
            .split(",")
            .map((e) => e.trim())
            .filter((e) => e.length > 0);
    }
    if (str.length === 1) {
        return str[0]
            ?.split(",")
            .map((e) => e.trim())
            .filter((e) => e.length > 0);
    }
    return str;
}
/**
 * Preprocessor for boolean values that handles string "false"/"0" correctly.
 * Zod's coerce.boolean() treats any non-empty string as true, which is not what we want.
 */
function parseBoolean(val) {
    if (val === undefined) {
        return undefined;
    }
    if (typeof val === "string") {
        if (val === "false") {
            return false;
        }
        if (val === "true") {
            return true;
        }
        throw new Error(`Invalid boolean value: ${val}`);
    }
    if (typeof val === "boolean") {
        return val;
    }
    if (typeof val === "number") {
        return val !== 0;
    }
    return !!val;
}
/** Allow overriding only to the allowed value */
function oneWayOverride(allowedValue) {
    return (oldValue, newValue) => {
        // Only allow override if setting to allowed value or current value
        if (newValue === oldValue) {
            return newValue;
        }
        if (newValue === allowedValue) {
            return newValue;
        }
        throw new Error(`Can only set to ${String(allowedValue)}`);
    };
}
/** Allow overriding only to a value lower than the specified value */
function onlyLowerThanBaseValueOverride() {
    return (oldValue, newValue) => {
        if (typeof oldValue !== "number") {
            throw new Error(`Unsupported type for base value for override: ${typeof oldValue}`);
        }
        if (typeof newValue !== "number") {
            throw new Error(`Unsupported type for new value for override: ${typeof newValue}`);
        }
        if (newValue >= oldValue) {
            throw new Error(`Can only set to a value lower than the base value`);
        }
        return newValue;
    };
}
/**
 * Allow overriding a log level only to a stricter (higher severity) value.
 * The ordered list must go from least to most severe.
 */
function onlyStricterLogLevelOverride(orderedLevels) {
    return (oldValue, newValue) => {
        if (typeof oldValue !== "string" || typeof newValue !== "string") {
            throw new Error(`Expected string log level values`);
        }
        const oldIdx = orderedLevels.indexOf(oldValue);
        const newIdx = orderedLevels.indexOf(newValue);
        if (oldIdx === -1 || newIdx === -1) {
            throw new Error(`Unknown log level`);
        }
        if (newIdx < oldIdx) {
            throw new Error(`Can only override to a stricter (higher severity) log level`);
        }
        return newValue;
    };
}
/** Allow overriding only to a subset of an array but not a superset */
function onlySubsetOfBaseValueOverride() {
    return (oldValue, newValue) => {
        if (!Array.isArray(oldValue)) {
            throw new Error(`Unsupported type for base value for override: ${typeof oldValue}`);
        }
        if (!Array.isArray(newValue)) {
            throw new Error(`Unsupported type for new value for override: ${typeof newValue}`);
        }
        if (newValue.length > oldValue.length) {
            throw new Error(`Can only override to a subset of the base value`);
        }
        if (!newValue.every((value) => oldValue.includes(value))) {
            throw new Error(`Can only override to a subset of the base value`);
        }
        return newValue;
    };
}
//# sourceMappingURL=configUtils.js.map