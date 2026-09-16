"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ExportedData = void 0;
const mcp_js_1 = require("@modelcontextprotocol/sdk/server/mcp.js");
const index_js_1 = require("../../common/logging/index.js");
const tool_js_1 = require("../../tools/tool.js");
class ExportedData {
    constructor(session) {
        this.session = session;
        this.name = "exported-data";
        this.description = "Data files exported in the current session.";
        this.uri = "exported-data://{exportName}";
        this.listResourcesCallback = () => {
            try {
                return {
                    resources: this.session.exportsManager.availableExports.map(({ exportName, exportTitle, exportURI }) => ({
                        name: exportName,
                        description: exportTitle,
                        uri: exportURI,
                        mimeType: "application/json",
                    })),
                };
            }
            catch (error) {
                this.session.logger.error({
                    id: index_js_1.LogId.exportedDataListError,
                    context: "Error when listing exported data resources",
                    message: error instanceof Error ? error.message : String(error),
                });
                return {
                    resources: [],
                };
            }
        };
        this.autoCompleteExportName = (value) => {
            try {
                return this.session.exportsManager.availableExports
                    .filter(({ exportName, exportTitle }) => {
                    const lcExportName = exportName.toLowerCase();
                    const lcExportTitle = exportTitle.toLowerCase();
                    const lcValue = value.toLowerCase();
                    return lcExportName.startsWith(lcValue) || lcExportTitle.includes(lcValue);
                })
                    .map(({ exportName }) => exportName);
            }
            catch (error) {
                this.session.logger.error({
                    id: index_js_1.LogId.exportedDataAutoCompleteError,
                    context: "Error when autocompleting exported data",
                    message: error instanceof Error ? error.message : String(error),
                });
                return [];
            }
        };
        this.readResourceCallback = async (url, { exportName }) => {
            try {
                if (typeof exportName !== "string") {
                    throw new Error("Cannot retrieve exported data, exportName not provided.");
                }
                const { content, docsTransformed } = await this.session.exportsManager.readExport(exportName);
                const text = (0, tool_js_1.formatUntrustedData)(`The exported data contains ${docsTransformed} documents.`, content)
                    .map((t) => t.text)
                    .join("\n");
                return {
                    contents: [
                        {
                            uri: url.href,
                            text,
                            mimeType: "application/json",
                        },
                    ],
                };
            }
            catch (error) {
                return {
                    contents: [
                        {
                            uri: url.href,
                            text: `Error reading ${url.href}: ${error instanceof Error ? error.message : String(error)}`,
                        },
                    ],
                    isError: true,
                };
            }
        };
    }
    register(server) {
        this.server = server;
        this.server.mcpServer.registerResource(this.name, new mcp_js_1.ResourceTemplate(this.uri, {
            /**
             * A few clients have the capability of listing templated
             * resources as well and this callback provides support for that
             * */
            list: this.listResourcesCallback,
            /**
             * This is to provide auto completion when user starts typing in
             * value for template variable, in our case, exportName */
            complete: {
                exportName: this.autoCompleteExportName,
            },
        }), { description: this.description }, this.readResourceCallback);
        this.session.exportsManager.on("export-available", (uri) => {
            server.sendResourceListChanged();
            server.sendResourceUpdated(uri);
        });
        this.session.exportsManager.on("export-expired", () => {
            server.sendResourceListChanged();
        });
    }
}
exports.ExportedData = ExportedData;
//# sourceMappingURL=exportedData.js.map