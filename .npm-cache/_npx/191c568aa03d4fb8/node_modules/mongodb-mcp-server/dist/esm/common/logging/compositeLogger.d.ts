import type { LoggerType, LogLevel, LogPayload } from "./index.js";
import { LoggerBase } from "./loggerBase.js";
export declare class CompositeLogger extends LoggerBase {
    protected readonly type?: LoggerType;
    private readonly loggers;
    private readonly attributes;
    constructor(...loggers: LoggerBase[]);
    addLogger(logger: LoggerBase): void;
    log(level: LogLevel, payload: LogPayload): void;
    protected logCore(): void;
    setAttribute(key: string, value: string): void;
}
//# sourceMappingURL=compositeLogger.d.ts.map