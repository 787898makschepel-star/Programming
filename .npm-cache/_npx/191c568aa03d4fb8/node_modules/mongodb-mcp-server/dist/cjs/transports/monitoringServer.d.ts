import type { DefaultMetrics, MonitoringServerFeature, Metrics, LoggerBase, UserConfig, MonitoringServerConstructorArgs } from "../lib.js";
import { ExpressBasedHttpServer } from "./expressBasedHttpServer.js";
export declare class MonitoringServer<TMetrics extends DefaultMetrics = DefaultMetrics> extends ExpressBasedHttpServer {
    private readonly features;
    private readonly metrics;
    constructor({ host, port, features, logger, metrics, }: {
        host: string;
        port: number;
        features: MonitoringServerFeature[];
        logger: LoggerBase;
        metrics: Metrics<TMetrics>;
    });
    static fromConfig<TMetrics extends DefaultMetrics = DefaultMetrics>({ userConfig, logger, metrics, }: {
        userConfig: UserConfig;
        logger: LoggerBase;
        metrics: Metrics<TMetrics>;
    }): MonitoringServer<TMetrics> | undefined;
    protected setupRoutes(): Promise<void>;
}
/**
 * A function to create a custom MonitoringServer instance.
 * When provided, the runner will use this function instead of the default MonitoringServer constructor.
 */
export type CreateMonitoringServerFn<TMetrics extends DefaultMetrics = DefaultMetrics> = (args: MonitoringServerConstructorArgs<TMetrics>) => MonitoringServer<TMetrics> | undefined;
/**
 * Creates a default MonitoringServer instance from the provided constructor arguments.
 */
export declare const createDefaultMonitoringServer: <TMetrics extends DefaultMetrics = DefaultMetrics>(args: MonitoringServerConstructorArgs<TMetrics>) => MonitoringServer<TMetrics>;
//# sourceMappingURL=monitoringServer.d.ts.map