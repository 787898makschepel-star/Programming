"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CompositeLogger = void 0;
const loggerBase_js_1 = require("./loggerBase.js");
class CompositeLogger extends loggerBase_js_1.LoggerBase {
    constructor(...loggers) {
        // composite logger does not redact, only the actual delegates do the work
        // so we don't need the Keychain here
        super(undefined);
        this.loggers = [];
        this.attributes = {};
        this.loggers = loggers;
    }
    addLogger(logger) {
        this.loggers.push(logger);
    }
    log(level, payload) {
        // Override the public method to avoid the base logger redacting the message payload
        for (const logger of this.loggers) {
            const attributes = Object.keys(this.attributes).length > 0 || payload.attributes
                ? { ...this.attributes, ...payload.attributes }
                : undefined;
            logger.log(level, { ...payload, attributes });
        }
    }
    logCore() {
        throw new Error("logCore should never be invoked on CompositeLogger");
    }
    setAttribute(key, value) {
        this.attributes[key] = value;
    }
}
exports.CompositeLogger = CompositeLogger;
//# sourceMappingURL=compositeLogger.js.map