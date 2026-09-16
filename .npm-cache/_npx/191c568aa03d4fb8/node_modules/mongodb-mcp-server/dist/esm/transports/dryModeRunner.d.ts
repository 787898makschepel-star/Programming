import { type CustomizableSessionOptions, TransportRunnerBase, type TransportRunnerConfig } from "./base.js";
import type { CustomizableServerOptions } from "../lib.js";
export type DryRunModeTestHelpers = {
    logger: {
        log(this: void, message: string): void;
        error(this: void, message: string): void;
    };
};
type DryRunModeRunnerConfig = TransportRunnerConfig & DryRunModeTestHelpers;
export declare class DryRunModeRunner extends TransportRunnerBase {
    private server;
    private consoleLogger;
    constructor({ logger, ...transportRunnerConfig }: DryRunModeRunnerConfig);
    start({ serverOptions, sessionOptions, }?: {
        serverOptions?: CustomizableServerOptions;
        sessionOptions?: CustomizableSessionOptions;
    }): Promise<void>;
    closeTransport(): Promise<void>;
    private dumpConfig;
    private dumpTools;
}
export {};
//# sourceMappingURL=dryModeRunner.d.ts.map