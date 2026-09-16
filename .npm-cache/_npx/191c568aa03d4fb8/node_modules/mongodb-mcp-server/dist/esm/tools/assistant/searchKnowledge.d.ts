import { z } from "zod";
import { type CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { type ToolArgs, type OperationType, type ToolCategory } from "../tool.js";
import { AssistantToolBase } from "./assistantTool.js";
export declare const SearchKnowledgeToolArgs: {
    query: z.ZodString;
    limit: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
    dataSources: z.ZodOptional<z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        versionLabel: z.ZodOptional<z.ZodString>;
    }, z.core.$strip>>>;
};
export type SearchKnowledgeResponse = {
    /** A list of search results */
    results: {
        /** The URL of the search result */
        url: string;
        /** The page title of the search result */
        title: string;
        /** The text of the page chunk returned from the search */
        text: string;
        /** Metadata for the search result */
        metadata: {
            /** A list of tags that describe the page */
            tags: string[];
            /** Additional metadata */
            [key: string]: unknown;
        };
    }[];
};
export declare const SearchKnowledgeToolName = "search-knowledge";
export declare class SearchKnowledgeTool extends AssistantToolBase {
    static toolName: string;
    static category: ToolCategory;
    static operationType: OperationType;
    description: string;
    argsShape: {
        query: z.ZodString;
        limit: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        dataSources: z.ZodOptional<z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            versionLabel: z.ZodOptional<z.ZodString>;
        }, z.core.$strip>>>;
    };
    protected execute(args: ToolArgs<typeof this.argsShape>): Promise<CallToolResult>;
}
//# sourceMappingURL=searchKnowledge.d.ts.map