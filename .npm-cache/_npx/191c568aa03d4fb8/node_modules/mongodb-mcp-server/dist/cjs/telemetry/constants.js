"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MACHINE_METADATA = void 0;
const packageInfo_js_1 = require("../common/packageInfo.js");
/**
 * Machine-specific metadata formatted for telemetry
 */
exports.MACHINE_METADATA = {
    mcp_server_version: packageInfo_js_1.packageInfo.version,
    mcp_server_name: packageInfo_js_1.packageInfo.mcpServerName,
    platform: (typeof process !== "undefined" && process.platform) || "browser",
    arch: (typeof process !== "undefined" && process.arch) || "unknown",
    os_type: (typeof process !== "undefined" && process.platform) || "unknown",
    os_version: (typeof process !== "undefined" && process.version) || "unknown",
};
//# sourceMappingURL=constants.js.map