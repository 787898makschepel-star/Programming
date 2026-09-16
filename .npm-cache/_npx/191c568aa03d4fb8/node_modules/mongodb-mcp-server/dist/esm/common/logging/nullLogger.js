import { LoggerBase } from "./loggerBase.js";
export class NullLogger extends LoggerBase {
    constructor() {
        super(undefined);
    }
    logCore() {
        // No-op logger, does not log anything
    }
}
//# sourceMappingURL=nullLogger.js.map