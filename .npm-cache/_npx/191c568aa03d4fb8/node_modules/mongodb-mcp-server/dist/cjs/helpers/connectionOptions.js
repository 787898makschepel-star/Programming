"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.setAppNameParamIfMissing = setAppNameParamIfMissing;
exports.validateConnectionString = validateConnectionString;
const mongodb_connection_string_url_1 = require("mongodb-connection-string-url");
/**
 * Sets the appName parameter with the extended format: appName--deviceId--clientName
 * Only sets the appName if it's not already present in the connection string
 * @param connectionString - The connection string to modify
 * @param components - The components to build the appName from
 * @returns The modified connection string
 */
async function setAppNameParamIfMissing({ connectionString, components, }) {
    const connectionStringUrl = new mongodb_connection_string_url_1.ConnectionString(connectionString);
    const searchParams = connectionStringUrl.typedSearchParams();
    // Only set appName if it's not already present
    if (searchParams.has("appName")) {
        return connectionStringUrl.toString();
    }
    const appName = components.appName || "unknown";
    const deviceId = components.deviceId ? await components.deviceId : "unknown";
    const clientName = components.clientName || "unknown";
    // Build the extended appName format: appName--deviceId--clientName
    const extendedAppName = `${appName}--${deviceId}--${clientName}`;
    searchParams.set("appName", extendedAppName);
    return connectionStringUrl.toString();
}
/**
 * Validates the connection string
 * @param connectionString - The connection string to validate
 * @param looseValidation - Whether to allow loose validation
 * @returns void
 * @throws Error if the connection string is invalid
 */
function validateConnectionString(connectionString, looseValidation) {
    try {
        new mongodb_connection_string_url_1.ConnectionString(connectionString, { looseValidation });
    }
    catch (error) {
        throw new Error(`Invalid connection string with error: ${error instanceof Error ? error.message : String(error)}`, { cause: error });
    }
}
//# sourceMappingURL=connectionOptions.js.map