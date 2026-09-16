import { LoggerBase } from "./loggerBase.js";
export class ConsoleLogger extends LoggerBase {
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
//# sourceMappingURL=consoleLogger.js.map