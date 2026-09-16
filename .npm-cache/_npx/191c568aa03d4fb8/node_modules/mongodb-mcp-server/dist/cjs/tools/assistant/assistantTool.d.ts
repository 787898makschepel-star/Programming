import { ToolBase, type ToolConstructorParams } from "../tool.js";
import type { TelemetryToolMetadata } from "../../telemetry/types.js";
import type { Server } from "../../server.js";
export declare abstract class AssistantToolBase extends ToolBase {
    protected server?: Server;
    protected baseUrl: URL;
    protected requiredHeaders: Headers;
    constructor(params: ToolConstructorParams);
    register(server: Server): boolean;
    protected resolveTelemetryMetadata(): TelemetryToolMetadata;
    protected callAssistantApi(args: {
        method: "GET" | "POST";
        endpoint: string;
        body?: unknown;
    }): Promise<Response>;
}
//# sourceMappingURL=assistantTool.d.ts.map