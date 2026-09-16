"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CONFIG_QUERY_PREFIX = exports.CONFIG_HEADER_PREFIX = exports.ConfigOverrideError = void 0;
exports.applyConfigOverrides = applyConfigOverrides;
exports.getConfigMeta = getConfigMeta;
exports.nameToConfigKey = nameToConfigKey;
const userConfig_js_1 = require("./userConfig.js");
class ConfigOverrideError extends Error {
    constructor(message) {
        super(message);
    }
}
exports.ConfigOverrideError = ConfigOverrideError;
exports.CONFIG_HEADER_PREFIX = "x-mongodb-mcp-";
exports.CONFIG_QUERY_PREFIX = "mongodbMcp";
/**
 * Applies config overrides from request context (headers and query parameters).
 * Query parameters take precedence over headers. Can be used within the createSessionConfig
 * hook to manually apply the overrides. Requires `allowRequestOverrides` to be enabled.
 *
 * @param baseConfig - The base user configuration
 * @param request - The request context containing headers and query parameters
 * @returns The configuration with overrides applied
 */
function applyConfigOverrides({ baseConfig, request, }) {
    if (!request) {
        return baseConfig;
    }
    const result = { ...baseConfig };
    const overridesFromHeaders = extractConfigOverrides("header", request.headers);
    const overridesFromQuery = extractConfigOverrides("query", request.query);
    // Only apply overrides if allowRequestOverrides is enabled
    if (!baseConfig.allowRequestOverrides &&
        (Object.keys(overridesFromHeaders).length > 0 || Object.keys(overridesFromQuery).length > 0)) {
        throw new ConfigOverrideError("Request overrides are not enabled");
    }
    // Apply header overrides first
    for (const [key, overrideValue] of Object.entries(overridesFromHeaders)) {
        assertValidConfigKey(key);
        const meta = getConfigMeta(key);
        const behavior = meta?.overrideBehavior || "not-allowed";
        const baseValue = baseConfig[key];
        const newValue = applyOverride(key, baseValue, overrideValue, behavior);
        result[key] = newValue;
    }
    // Apply query overrides (with precedence), but block secret fields
    for (const [key, overrideValue] of Object.entries(overridesFromQuery)) {
        assertValidConfigKey(key);
        const meta = getConfigMeta(key);
        // Prevent overriding secret fields via query params
        if (meta?.isSecret) {
            throw new ConfigOverrideError(`Config key ${key} can only be overridden with headers.`);
        }
        const behavior = meta?.overrideBehavior || "not-allowed";
        const baseValue = baseConfig[key];
        const newValue = applyOverride(key, baseValue, overrideValue, behavior);
        result[key] = newValue;
    }
    return result;
}
/**
 * Extracts config overrides from HTTP headers or query parameters.
 */
function extractConfigOverrides(mode, source) {
    if (!source) {
        return {};
    }
    const overrides = {};
    for (const [name, value] of Object.entries(source)) {
        const configKey = nameToConfigKey(mode, name);
        if (!configKey) {
            continue;
        }
        assertValidConfigKey(configKey);
        const parsedValue = parseConfigValue(configKey, value);
        if (parsedValue !== undefined) {
            overrides[configKey] = parsedValue;
        }
    }
    return overrides;
}
function assertValidConfigKey(key) {
    if (!(key in userConfig_js_1.UserConfigSchema.shape)) {
        throw new ConfigOverrideError(`Invalid config key: ${key}`);
    }
}
/**
 * Gets the schema metadata for a config key.
 */
function getConfigMeta(key) {
    return userConfig_js_1.configRegistry.get(userConfig_js_1.UserConfigSchema.shape[key]);
}
/**
 * Parses a string value to the appropriate type using the Zod schema.
 */
function parseConfigValue(key, value) {
    const fieldSchema = userConfig_js_1.UserConfigSchema.shape[key];
    if (!fieldSchema) {
        throw new ConfigOverrideError(`Invalid config key: ${key}`);
    }
    const result = fieldSchema.safeParse(value);
    if (!result.success) {
        throw new ConfigOverrideError(`Invalid configuration for the following fields:\n${result.error.issues.map((issue) => `${key} - ${issue.message}`).join("\n")}`);
    }
    return result.data;
}
/**
 * Converts a header/query name to its config key format.
 * Example: "x-mongodb-mcp-read-only" -> "readOnly"
 * Example: "mongodbMcpReadOnly" -> "readOnly"
 */
function nameToConfigKey(mode, name) {
    const lowerCaseName = name.toLowerCase();
    if (mode === "header" && lowerCaseName.startsWith(exports.CONFIG_HEADER_PREFIX)) {
        const normalized = lowerCaseName.substring(exports.CONFIG_HEADER_PREFIX.length);
        // Convert kebab-case to camelCase
        return normalized.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    }
    if (mode === "query" && name.startsWith(exports.CONFIG_QUERY_PREFIX)) {
        const withoutPrefix = name.substring(exports.CONFIG_QUERY_PREFIX.length);
        // Convert first letter to lowercase to get config key
        return withoutPrefix.charAt(0).toLowerCase() + withoutPrefix.slice(1);
    }
    return undefined;
}
function applyOverride(key, baseValue, overrideValue, behavior) {
    if (typeof behavior === "function") {
        try {
            return behavior(baseValue, overrideValue);
        }
        catch (error) {
            throw new ConfigOverrideError(`Cannot apply override for ${key}: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    switch (behavior) {
        case "override":
            return overrideValue;
        case "merge":
            if (Array.isArray(baseValue) && Array.isArray(overrideValue)) {
                return [...baseValue, ...overrideValue];
            }
            throw new ConfigOverrideError(`Cannot merge non-array values for ${key}`);
        case "not-allowed":
            throw new ConfigOverrideError(`Config key ${key} is not allowed to be overridden`);
        default:
            return baseValue;
    }
}
//# sourceMappingURL=configOverrides.js.map