import type { Server } from "../../server.js";
import type { UserConfig } from "../config/userConfig.js";
import type { Keychain } from "../keychain.js";
import { type LoggerType, type LogLevel, type LogPayload } from "./loggingTypes.js";
import { LoggerBase } from "./loggerBase.js";
export declare class McpLogger<TUserConfig extends UserConfig = UserConfig, TContext = unknown> extends LoggerBase {
    private readonly server;
    constructor(server: Server<TUserConfig, TContext>, keychain: Keychain);
    protected readonly type: LoggerType;
    protected logCore(level: LogLevel, payload: LogPayload): void;
}
//# sourceMappingURL=mcpLogger.d.ts.map