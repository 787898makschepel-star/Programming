import type { Keychain } from "../keychain.js";
import type { LogLevel, LogPayload, LoggerType } from "./index.js";
import { LoggerBase } from "./loggerBase.js";
export declare class DiskLogger extends LoggerBase<{
    initialized: [];
}> {
    private bufferedMessages;
    private logWriter?;
    constructor(logPath: string, onError: (error: Error) => void, keychain: Keychain);
    private initialize;
    protected type: LoggerType;
    protected logCore(level: LogLevel, payload: LogPayload): void;
}
//# sourceMappingURL=diskLogger.d.ts.map