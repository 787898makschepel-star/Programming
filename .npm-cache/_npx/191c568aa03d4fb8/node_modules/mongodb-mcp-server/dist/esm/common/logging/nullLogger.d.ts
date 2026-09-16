import type { LoggerType } from "./loggingTypes.js";
import { LoggerBase } from "./loggerBase.js";
export declare class NullLogger extends LoggerBase {
    protected type?: LoggerType;
    constructor();
    protected logCore(): void;
}
//# sourceMappingURL=nullLogger.d.ts.map