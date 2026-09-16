#!/usr/bin/env node
"use strict";
/* eslint-disable no-console */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.handleDryRunRequest = handleDryRunRequest;
function enableFipsIfRequested() {
    let fipsError;
    const tlsFIPSMode = process.argv.includes("--tlsFIPSMode");
    if (tlsFIPSMode) {
        try {
            // eslint-disable-next-line
            require("crypto").setFips(1);
        }
        catch (err) {
            fipsError ?? (fipsError = err);
        }
    }
    if (tlsFIPSMode) {
        if (!fipsError && !crypto_1.default.getFips()) {
            fipsError = new Error("FIPS mode not enabled despite requested due to unknown error.");
        }
    }
    if (fipsError) {
        if (process.config.variables.node_shared_openssl) {
            console.error("Could not enable FIPS mode. Please ensure that your system OpenSSL installation supports FIPS.");
        }
        else {
            console.error("Could not enable FIPS mode. This installation does not appear to support FIPS.");
        }
        console.error("Error details:");
        console.error(fipsError);
        process.exit(1);
    }
}
enableFipsIfRequested();
const crypto_1 = __importDefault(require("crypto"));
const index_js_1 = require("./common/logging/index.js");
const parseUserConfig_js_1 = require("./common/config/parseUserConfig.js");
const packageInfo_js_1 = require("./common/packageInfo.js");
const stdio_js_1 = require("./transports/stdio.js");
const streamableHttp_js_1 = require("./transports/streamableHttp.js");
const devtools_proxy_support_1 = require("@mongodb-js/devtools-proxy-support");
const keychain_js_1 = require("./common/keychain.js");
const dryModeRunner_js_1 = require("./transports/dryModeRunner.js");
const setupMcpServer_js_1 = require("./setup/setupMcpServer.js");
async function main() {
    (0, devtools_proxy_support_1.systemCA)().catch(() => undefined); // load system CA asynchronously as in mongosh
    const args = process.argv.slice(2);
    const isSetupRequested = args[0] === "setup";
    if (isSetupRequested) {
        // remove the "setup" argument so it doesn't interfere with arg parsings
        args.shift();
    }
    const { error, warnings, parsed: config, } = (0, parseUserConfig_js_1.parseUserConfig)({
        args: process.argv.slice(2),
    });
    if (!config || (error && error.length)) {
        console.error(`${error}
- Refer to https://www.mongodb.com/docs/mcp-server/get-started/ for setting up the MCP Server.`);
        process.exit(1);
    }
    if (warnings && warnings.length) {
        console.warn(`${warnings.join("\n")}
- Refer to https://www.mongodb.com/docs/mcp-server/get-started/ for setting up the MCP Server.`);
    }
    if (config.help) {
        handleHelpRequest();
    }
    if (config.version) {
        handleVersionRequest();
    }
    if (isSetupRequested) {
        await (0, setupMcpServer_js_1.runSetup)(config);
    }
    if (config.dryRun) {
        await handleDryRunRequest(config);
    }
    const transportRunner = config.transport === "stdio"
        ? new stdio_js_1.StdioRunner({
            userConfig: config,
        })
        : new streamableHttp_js_1.StreamableHttpRunner({
            userConfig: config,
        });
    const shutdown = () => {
        transportRunner.logger.info({
            id: index_js_1.LogId.serverCloseRequested,
            context: "server",
            message: `Server close requested`,
        });
        transportRunner
            .close()
            .then(() => {
            transportRunner.logger.info({
                id: index_js_1.LogId.serverClosed,
                context: "server",
                message: `Server closed`,
            });
            process.exit(0);
        })
            .catch((error) => {
            transportRunner.logger.error({
                id: index_js_1.LogId.serverCloseFailure,
                context: "server",
                message: `Error closing server: ${error}`,
            });
            process.exit(1);
        });
    };
    process.on("SIGINT", shutdown);
    process.on("SIGABRT", shutdown);
    process.on("SIGTERM", shutdown);
    process.on("SIGQUIT", shutdown);
    try {
        await transportRunner.start();
    }
    catch (error) {
        transportRunner.logger.info({
            id: index_js_1.LogId.serverCloseRequested,
            context: "server",
            message: `Closing server due to error: ${error}`,
        });
        try {
            await transportRunner.close();
            transportRunner.logger.info({
                id: index_js_1.LogId.serverClosed,
                context: "server",
                message: "Server closed",
            });
        }
        catch (error) {
            transportRunner.logger.error({
                id: index_js_1.LogId.serverCloseFailure,
                context: "server",
                message: `Error closing server: ${error}`,
            });
        }
        throw error;
    }
}
main().catch((error) => {
    // At this point, we may be in a very broken state, so we can't rely on the logger
    // being functional. Instead, create a brand new ConsoleLogger and log the error
    // to the console.
    const logger = new index_js_1.ConsoleLogger(keychain_js_1.Keychain.root);
    logger.emergency({
        id: index_js_1.LogId.serverStartFailure,
        context: "server",
        message: `Fatal error running server: ${error}`,
    });
    process.exit(1);
});
function handleHelpRequest() {
    console.log("For usage information refer to the README.md:");
    console.log("https://github.com/mongodb-js/mongodb-mcp-server?tab=readme-ov-file#quick-start");
    process.exit(0);
}
function handleVersionRequest() {
    console.log(packageInfo_js_1.packageInfo.version);
    process.exit(0);
}
async function handleDryRunRequest(config) {
    try {
        const runner = new dryModeRunner_js_1.DryRunModeRunner({
            userConfig: config,
            logger: {
                log(message) {
                    console.log(message);
                },
                error(message) {
                    console.error(message);
                },
            },
        });
        await runner.start();
        await runner.close();
        process.exit(0);
    }
    catch (error) {
        console.error(`Fatal error running server in dry run mode: ${error}`);
        process.exit(1);
    }
}
//# sourceMappingURL=index.js.map