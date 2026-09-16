import { formatUntrustedData } from "../tool.js";
import { AssistantToolBase } from "./assistantTool.js";
import { LogId } from "../../common/logging/index.js";
import { stringify as yamlStringify } from "yaml";
export const ListKnowledgeSourcesToolName = "list-knowledge-sources";
export class ListKnowledgeSourcesTool extends AssistantToolBase {
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
                id: LogId.assistantListKnowledgeSourcesError,
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
        const text = yamlStringify(dataSources.map((ds) => {
            const currentVersion = ds.versions.find(({ isCurrent }) => isCurrent)?.label;
            return currentVersion ? { ...ds, currentVersion } : ds;
        }));
        return {
            content: formatUntrustedData(`Found ${dataSources.length} data sources in the MongoDB Assistant knowledge base.`, text),
        };
    }
}
ListKnowledgeSourcesTool.toolName = ListKnowledgeSourcesToolName;
ListKnowledgeSourcesTool.category = "assistant";
ListKnowledgeSourcesTool.operationType = "read";
//# sourceMappingURL=listKnowledgeSources.js.map