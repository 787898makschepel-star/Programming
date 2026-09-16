import type { UserConfig } from "./userConfig.js";
import { UserConfigSchema } from "./userConfig.js";
import type { RequestContext } from "../../transports/base.js";
import type { ConfigFieldMeta } from "./configUtils.js";
export declare class ConfigOverrideError extends Error {
    constructor(message: string);
}
export declare const CONFIG_HEADER_PREFIX = "x-mongodb-mcp-";
export declare const CONFIG_QUERY_PREFIX = "mongodbMcp";
/**
 * Applies config overrides from request context (headers and query parameters).
 * Query parameters take precedence over headers. Can be used within the createSessionConfig
 * hook to manually apply the overrides. Requires `allowRequestOverrides` to be enabled.
 *
 * @param baseConfig - The base user configuration
 * @param request - The request context containing headers and query parameters
 * @returns The configuration with overrides applied
 */
export declare function applyConfigOverrides<TUserConfig extends UserConfig = UserConfig>({ baseConfig, request, }: {
    baseConfig: TUserConfig;
    request?: RequestContext;
}): TUserConfig;
/**
 * Gets the schema metadata for a config key.
 */
export declare function getConfigMeta(key: keyof typeof UserConfigSchema.shape): ConfigFieldMeta | undefined;
/**
 * Converts a header/query name to its config key format.
 * Example: "x-mongodb-mcp-read-only" -> "readOnly"
 * Example: "mongodbMcpReadOnly" -> "readOnly"
 */
export declare function nameToConfigKey(mode: "header" | "query", name: string): string | undefined;
//# sourceMappingURL=configOverrides.d.ts.map