import type { Keychain } from "../keychain.js";
import type { LoggerType, LogLevel, LogPayload } from "./index.js";
import { LoggerBase } from "./loggerBase.js";
export declare class ConsoleLogger extends LoggerBase {
    protected readonly type: LoggerType;
    constructor(keychain: Keychain);
    protected logCore(level: LogLevel, payload: LogPayload): void;
    private serializeAttributes;
}
//# sourceMappingURL=consoleLogger.d.ts.map