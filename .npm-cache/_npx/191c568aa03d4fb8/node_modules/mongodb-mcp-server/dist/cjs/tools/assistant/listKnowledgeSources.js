"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ListKnowledgeSourcesTool = exports.ListKnowledgeSourcesToolName = void 0;
const tool_js_1 = require("../tool.js");
const assistantTool_js_1 = require("./assistantTool.js");
const index_js_1 = require("../../common/logging/index.js");
const yaml_1 = require("yaml");
exports.ListKnowledgeSourcesToolName = "list-knowledge-sources";
class ListKnowledgeSourcesTool extends assistantTool_js_1.AssistantToolBase {
    constructor() {
        super(...arguments);
        this.description = `List available data sources in the MongoDB Assistant knowledge base. Use this to explore available data sources or to find search filter parameters to use in search-knowledge.`;
        this.argsShape = {};
    }
    async execute() {
        const response = await this.callAssistantApi({
            method: "GET",
            endpoint: "content/sources",
        });
        if (!response.ok) {
            const message = `Failed to list knowledge sources: ${response.statusText}`;
            this.session.logger.debug({
                id: index_js_1.LogId.assistantListKnowledgeSourcesError,
                context: "assistant-list-knowledge-sources",
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
        const { dataSources } = (await response.json());
        const text = (0, yaml_1.stringify)(dataSources.map((ds) => {
            const currentVersion = ds.versions.find(({ isCurrent }) => isCurrent)?.label;
            return currentVersion ? { ...ds, currentVersion } : ds;
        }));
        return {
            content: (0, tool_js_1.formatUntrustedData)(`Found ${dataSources.length} data sources in the MongoDB Assistant knowledge base.`, text),
        };
    }
}
exports.ListKnowledgeSourcesTool = ListKnowledgeSourcesTool;
ListKnowledgeSourcesTool.toolName = exports.ListKnowledgeSourcesToolName;
ListKnowledgeSourcesTool.category = "assistant";
ListKnowledgeSourcesTool.operationType = "read";
//# sourceMappingURL=listKnowledgeSources.js.map