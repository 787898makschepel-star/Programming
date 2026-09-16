import { MCP_LOG_LEVELS } from "./loggingTypes.js";
import { LoggerBase } from "./loggerBase.js";
export class McpLogger extends LoggerBase {
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
        const minimumLevel = MCP_LOG_LEVELS.indexOf(this.server.mcpLogLevel);
        const currentLevel = MCP_LOG_LEVELS.indexOf(level);
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
//# sourceMappingURL=mcpLogger.js.map