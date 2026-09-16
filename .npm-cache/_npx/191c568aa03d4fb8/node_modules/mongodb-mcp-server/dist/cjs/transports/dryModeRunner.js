"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DryRunModeRunner = void 0;
const inMemoryTransport_js_1 = require("./inMemoryTransport.js");
const base_js_1 = require("./base.js");
class DryRunModeRunner extends base_js_1.TransportRunnerBase {
    constructor({ logger, ...transportRunnerConfig }) {
        super(transportRunnerConfig);
        this.consoleLogger = logger;
    }
    async start({ serverOptions, sessionOptions, } = {}) {
        this.server = await this.createServer({ serverOptions, sessionOptions });
        const transport = new inMemoryTransport_js_1.InMemoryTransport();
        await this.server.connect(transport);
        this.dumpConfig();
        this.dumpTools();
    }
    async closeTransport() {
        await this.server?.close();
    }
    dumpConfig() {
        this.consoleLogger.log("Configuration:");
        this.consoleLogger.log(JSON.stringify(this.userConfig, null, 2));
    }
    dumpTools() {
        const tools = this.server?.tools
            .filter((tool) => tool.isEnabled())
            .map((tool) => ({
            name: tool.name,
            category: tool.category,
        })) ?? [];
        this.consoleLogger.log("Enabled tools:");
        this.consoleLogger.log(JSON.stringify(tools, null, 2));
    }
}
exports.DryRunModeRunner = DryRunModeRunner;
//# sourceMappingURL=dryModeRunner.js.map