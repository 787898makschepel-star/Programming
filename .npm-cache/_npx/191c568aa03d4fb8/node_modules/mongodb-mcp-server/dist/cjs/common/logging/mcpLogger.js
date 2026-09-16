"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.McpLogger = void 0;
const loggingTypes_js_1 = require("./loggingTypes.js");
const loggerBase_js_1 = require("./loggerBase.js");
class McpLogger extends loggerBase_js_1.LoggerBase {
    constructor(server, keychain) {
        super(keychain);
        this.server = server;
        this.type = "mcp";
    }
    logCore(level, payload) {
        // Only log if the server is connected
        if (!this.server.mcpServer.isConnected()) {
            return;
        }
        const minimumLevel = loggingTypes_js_1.MCP_LOG_LEVELS.indexOf(this.server.mcpLogLevel);
        const currentLevel = loggingTypes_js_1.MCP_LOG_LEVELS.indexOf(level);
        if (minimumLevel > currentLevel) {
            // Don't log if the requested level is lower than the minimum level
            return;
        }
        void this.server.mcpServer.server.sendLoggingMessage({
            level,
            data: `[${payload.context}]: ${payload.message}`,
        });
    }
}
exports.McpLogger = McpLogger;
//# sourceMappingURL=mcpLogger.js.map