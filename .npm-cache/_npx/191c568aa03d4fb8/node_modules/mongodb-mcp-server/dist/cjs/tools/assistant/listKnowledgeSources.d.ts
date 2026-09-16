import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { type OperationType, type ToolCategory } from "../tool.js";
import { AssistantToolBase } from "./assistantTool.js";
export type KnowledgeSource = {
    /** The name of the data source */
    id: string;
    /** The type of the data source */
    type: string;
    /** A list of available versions for this data source */
    versions: {
        /** The version label of the data source */
        label: string;
        /** Whether this version is the current/default version */
        isCurrent: boolean;
    }[];
};
export type ListKnowledgeSourcesResponse = {
    dataSources: KnowledgeSource[];
};
export declare const ListKnowledgeSourcesToolName = "list-knowledge-sources";
export declare class ListKnowledgeSourcesTool extends AssistantToolBase {
    static toolName: string;
    static category: ToolCategory;
    static operationType: OperationType;
    description: string;
    argsShape: {};
    protected execute(): Promise<CallToolResult>;
}
//# sourceMappingURL=listKnowledgeSources.d.ts.map