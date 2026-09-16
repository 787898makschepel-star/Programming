import fs from "fs/promises";
import { MongoLogManager } from "mongodb-log-writer";
import { LoggerBase } from "./loggerBase.js";
export class DiskLogger extends LoggerBase {
    constructor(logPath, onError, keychain) {
        super(keychain);
        this.bufferedMessages = [];
        this.type = "disk";
        void this.initialize(logPath, onError);
    }
    async initialize(logPath, onError) {
        try {
            await fs.mkdir(logPath, { recursive: true });
            const manager = new MongoLogManager({
                directory: logPath,
                retentionDays: 30,
                // eslint-disable-next-line no-console
                onwarn: console.warn,
                // eslint-disable-next-line no-console
                onerror: console.error,
                gzip: false,
                retentionGB: 1,
            });
            await manager.cleanupOldLogFiles();
            this.logWriter = await manager.createLogWriter();
            for (const message of this.bufferedMessages) {
                this.logCore(message.level, message.payload);
            }
            this.bufferedMessages = [];
            this.emit("initialized");
        }
        catch (error) {
            onError(error);
        }
    }
    logCore(level, payload) {
        if (!this.logWriter) {
            // If the log writer is not initialized, buffer the message
            this.bufferedMessages.push({ level, payload });
            return;
        }
        const { id, context, message } = payload;
        const mongoDBLevel = this.mapToMongoDBLogLevel(level);
        this.logWriter[mongoDBLevel]("MONGODB-MCP", id, context, message, payload.attributes);
    }
}
//# sourceMappingURL=diskLogger.js.map