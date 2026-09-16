import { Registry, collectDefaultMetrics } from "prom-client";
export class PrometheusMetrics {
    constructor({ definitions, registry, collectProcessMetrics = false }) {
        this.registry = registry ?? new Registry();
        if (collectProcessMetrics) {
            collectDefaultMetrics({ register: this.registry });
        }
        this.definitions = definitions;
        for (const key in this.definitions) {
            const metric = this.definitions[key];
            this.registry.registerMetric(metric);
        }
    }
    get(key) {
        return this.definitions[key];
    }
    async getMetrics() {
        return this.registry.metrics();
    }
}
//# sourceMappingURL=prometheusMetrics.js.map