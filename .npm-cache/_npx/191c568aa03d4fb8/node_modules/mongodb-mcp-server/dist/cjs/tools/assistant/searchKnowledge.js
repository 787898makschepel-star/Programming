"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SearchKnowledgeTool = exports.SearchKnowledgeToolName = exports.SearchKnowledgeToolArgs = void 0;
const zod_1 = require("zod");
const tool_js_1 = require("../tool.js");
const assistantTool_js_1 = require("./assistantTool.js");
const index_js_1 = require("../../common/logging/index.js");
const yaml_1 = require("yaml");
exports.SearchKnowledgeToolArgs = {
    query: zod_1.z
        .string()
        .describe("A natural language query to search for in the MongoDB Assistant knowledge base. This should be a single question or a topic that is relevant to the user's MongoDB use case."),
    limit: zod_1.z.number().min(1).max(100).optional().default(5).describe("The maximum number of results to return"),
    dataSources: zod_1.z
        .array(zod_1.z.object({
        name: zod_1.z.string().describe("The name of the data source"),
        versionLabel: zod_1.z.string().optional().describe("The version label of the data source"),
    }))
        .optional()
        .describe(`A list of one or more data sources to limit the search to. You can specify a specific version of a data source by providing the version label. If not provided, the latest version of all data sources will be searched. Available data sources and their versions can be listed by calling the list-knowledge-sources tool.`),
};
exports.SearchKnowledgeToolName = "search-knowledge";
class SearchKnowledgeTool extends assistantTool_js_1.AssistantToolBase {
    constructor() {
        super(...arguments);
        this.description = "Search for information in the MongoDB Assistant knowledge base. This includes official documentation, curated expert guidance, and other resources provided by MongoDB. Supports filtering by data source and version.";
        this.argsShape = {
            ...exports.SearchKnowledgeToolArgs,
        };
    }
    async execute(args) {
        const response = await this.callAssistantApi({
            method: "POST",
            endpoint: "content/search",
            body: args,
        });
        if (!response.ok) {
            const message = `Failed to search knowledge base: ${response.statusText}`;
            this.session.logger.debug({
                id: index_js_1.LogId.assistantSearchKnowledgeError,
                context: "assistant-search-knowledge",
                message,
            });
            return {
                content: [
                    {
                        type: "text",
                        text: message,
                    },
                ],
                isError: true,
            };
        }
        const { results } = (await response.json());
        const text = (0, yaml_1.stringify)(results);
        return {
            content: (0, tool_js_1.formatUntrustedData)(`Found ${results.length} results in the MongoDB Assistant knowledge base.`, text),
        };
    }
}
exports.SearchKnowledgeTool = SearchKnowledgeTool;
SearchKnowledgeTool.toolName = exports.SearchKnowledgeToolName;
SearchKnowledgeTool.category = "assistant";
SearchKnowledgeTool.operationType = "read";
//# sourceMappingURL=searchKnowledge.js.map