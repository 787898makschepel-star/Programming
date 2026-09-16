"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DiskLogger = void 0;
const promises_1 = __importDefault(require("fs/promises"));
const mongodb_log_writer_1 = require("mongodb-log-writer");
const loggerBase_js_1 = require("./loggerBase.js");
class DiskLogger extends loggerBase_js_1.LoggerBase {
    constructor(logPath, onError, keychain) {
        super(keychain);
        this.bufferedMessages = [];
        this.type = "disk";
        void this.initialize(logPath, onError);
    }
    async initialize(logPath, onError) {
        try {
            await promises_1.default.mkdir(logPath, { recursive: true });
            const manager = new mongodb_log_writer_1.MongoLogManager({
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
exports.DiskLogger = DiskLogger;
//# sourceMappingURL=diskLogger.js.map