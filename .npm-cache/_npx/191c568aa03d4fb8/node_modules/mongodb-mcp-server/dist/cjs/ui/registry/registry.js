"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.UIRegistry = void 0;
const loaders_js_1 = require("../lib/loaders.js");
const uiLoaders = loaders_js_1.uiLoaders;
/**
 * UI Registry that manages bundled UI HTML strings for tools.
 */
class UIRegistry {
    constructor(options) {
        this.cache = new Map();
        this.customUIs = options?.customUIs;
    }
    /**
     * Gets the UI HTML string for a tool, or null if none exists.
     */
    async get(toolName) {
        if (this.customUIs) {
            const customUI = await this.customUIs(toolName);
            if (customUI !== null && customUI !== undefined) {
                return customUI;
            }
        }
        const cached = this.cache.get(toolName);
        if (cached !== undefined) {
            return cached;
        }
        const loader = uiLoaders[toolName];
        if (!loader) {
            return null;
        }
        try {
            const html = await loader();
            if (html === undefined) {
                return null;
            }
            this.cache.set(toolName, html);
            return html;
        }
        catch {
            return null;
        }
    }
}
exports.UIRegistry = UIRegistry;
//# sourceMappingURL=registry.js.map