"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConsoleLogger = void 0;
const loggerBase_js_1 = require("./loggerBase.js");
class ConsoleLogger extends loggerBase_js_1.LoggerBase {
    constructor(keychain) {
        super(keychain);
        this.type = "console";
    }
    logCore(level, payload) {
        const { id, context, message } = payload;
        // eslint-disable-next-line no-console
        console.error(`[${level.toUpperCase()}] ${id.__value} - ${context}: ${message}${this.serializeAttributes(payload.attributes)}`);
    }
    serializeAttributes(attributes) {
        if (!attributes || Object.keys(attributes).length === 0) {
            return "";
        }
        return ` (${Object.entries(attributes)
            .map(([key, value]) => `${key}=${value}`)
            .join(", ")})`;
    }
}
exports.ConsoleLogger = ConsoleLogger;
//# sourceMappingURL=consoleLogger.js.map