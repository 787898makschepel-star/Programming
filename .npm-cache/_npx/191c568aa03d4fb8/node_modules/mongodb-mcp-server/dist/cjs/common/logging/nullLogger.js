"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NullLogger = void 0;
const loggerBase_js_1 = require("./loggerBase.js");
class NullLogger extends loggerBase_js_1.LoggerBase {
    constructor() {
        super(undefined);
    }
    logCore() {
        // No-op logger, does not log anything
    }
}
exports.NullLogger = NullLogger;
//# sourceMappingURL=nullLogger.js.map