import { Registry } from "prom-client";
import type { Metrics, MetricDefinitions, PrometheusMetricsOptions } from "./types.js";
export declare class PrometheusMetrics<TMetrics extends MetricDefinitions> implements Metrics<TMetrics> {
    readonly registry: Registry;
    private readonly definitions;
    constructor({ definitions, registry, collectProcessMetrics }: PrometheusMetricsOptions<TMetrics>);
    get<K extends keyof TMetrics>(key: K): TMetrics[K];
    getMetrics(): Promise<string>;
}
//# sourceMappingURL=prometheusMetrics.d.ts.map