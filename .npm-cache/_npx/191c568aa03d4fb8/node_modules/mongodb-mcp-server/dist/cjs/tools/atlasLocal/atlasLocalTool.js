"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AtlasLocalToolBase = exports.AtlasLocalToolMetadataDeploymentIdKey = void 0;
const tool_js_1 = require("../tool.js");
const index_js_1 = require("../../common/logging/index.js");
exports.AtlasLocalToolMetadataDeploymentIdKey = "deploymentId";
class AtlasLocalToolBase extends tool_js_1.ToolBase {
    verifyAllowed() {
        return this.session.atlasLocalClient !== undefined && super.verifyAllowed();
    }
    async execute(args, 
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _context) {
        const client = this.session.atlasLocalClient;
        // If the client is not found, throw an error
        // This should never happen:
        // - atlas-local tools are only added after the client is set
        //   this means that if we were unable to get the client, the tool will not be registered
        // - in case the tool was registered by accident
        //   verifyAllowed would still return false preventing the tool from being registered,
        //   preventing the tool from being executed
        if (!client) {
            return {
                content: [
                    {
                        type: "text",
                        text: `Something went wrong on our end, this tool should have been disabled but it was not.
please log a ticket here: https://github.com/mongodb-js/mongodb-mcp-server/issues/new?template=bug_report.yml`,
                    },
                ],
                isError: true,
            };
        }
        return this.executeWithAtlasLocalClient(args, { client });
    }
    async lookupDeploymentId(client, containerId) {
        try {
            // Lookup and return the deployment id for telemetry metadata.
            return await client.getDeploymentId(containerId);
        }
        catch (error) {
            this.session.logger.debug({
                id: index_js_1.LogId.telemetryMetadataError,
                context: "tool",
                message: `Error looking up deployment ID: ${String(error)}`,
            });
            return undefined;
        }
    }
    async lookupTelemetryMetadata(client, containerId) {
        if (!this.telemetry.isTelemetryEnabled()) {
            return {};
        }
        const deploymentId = await this.lookupDeploymentId(client, containerId);
        if (deploymentId === undefined) {
            return {};
        }
        return {
            [exports.AtlasLocalToolMetadataDeploymentIdKey]: deploymentId,
        };
    }
    handleError(error, args) {
        // Error Handling for expected Atlas Local errors go here
        const errorMessage = error instanceof Error ? error.message : String(error);
        // Check if Docker daemon is not running
        if (errorMessage.includes("Cannot connect to the Docker daemon") ||
            errorMessage.includes("Is the docker daemon running") ||
            errorMessage.includes("connect ENOENT") ||
            errorMessage.includes("ECONNREFUSED")) {
            return {
                content: [
                    {
                        type: "text",
                        text: "Docker is not running. Please start Docker and try again. Atlas Local tools require Docker to be running.",
                    },
                ],
                isError: true,
            };
        }
        if (errorMessage.includes("No such container")) {
            const deploymentName = "deploymentName" in args ? args.deploymentName : "the specified deployment";
            return {
                content: [
                    {
                        type: "text",
                        text: `The Atlas Local deployment "${deploymentName}" was not found. Please check the deployment name or use "atlas-local-list-deployments" to see available deployments.`,
                    },
                ],
                isError: true,
            };
        }
        // For other types of errors, use the default error handling from the base class
        return super.handleError(error, args);
    }
    resolveTelemetryMetadata(_args, { result }) {
        const toolMetadata = {};
        // Atlas Local tools set the deployment ID in the result metadata for telemetry
        // If the deployment ID is set, we use it for telemetry
        const resultDeploymentId = result._meta?.[exports.AtlasLocalToolMetadataDeploymentIdKey];
        if (resultDeploymentId !== undefined && typeof resultDeploymentId === "string") {
            toolMetadata.atlas_local_deployment_id = resultDeploymentId;
            toolMetadata.connection_host_type = "atlas_local";
        }
        return toolMetadata;
    }
}
exports.AtlasLocalToolBase = AtlasLocalToolBase;
AtlasLocalToolBase.category = "atlas-local";
//# sourceMappingURL=atlasLocalTool.js.map