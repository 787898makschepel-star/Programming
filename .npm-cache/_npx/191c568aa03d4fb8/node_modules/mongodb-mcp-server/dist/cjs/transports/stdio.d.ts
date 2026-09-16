import type { CustomizableServerOptions } from "./base.js";
import type { CustomizableSessionOptions } from "./base.js";
import { TransportRunnerBase, type TransportRunnerConfig } from "./base.js";
import type { UserConfig } from "../lib.js";
import type { DefaultMetrics } from "@mongodb-js/mcp-metrics";
export declare class StdioRunner<TUserConfig extends UserConfig = UserConfig, TContext = unknown, TMetrics extends DefaultMetrics = DefaultMetrics> extends TransportRunnerBase<TUserConfig, TContext, TMetrics> {
    private server;
    constructor(config: TransportRunnerConfig<TUserConfig, TMetrics>);
    start({ serverOptions, sessionOptions, }?: {
        serverOptions?: CustomizableServerOptions<TUserConfig, TContext>;
        sessionOptions?: CustomizableSessionOptions<TUserConfig>;
    }): Promise<void>;
    closeTransport(): Promise<void>;
}
//# sourceMappingURL=stdio.d.ts.map