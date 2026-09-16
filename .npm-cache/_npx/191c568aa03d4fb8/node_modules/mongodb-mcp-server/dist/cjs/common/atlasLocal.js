"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultCreateAtlasLocalClient = void 0;
const index_js_1 = require("./logging/index.js");
class DefaultLibraryLoader {
    constructor() {
        this.isAtlasLocalSupported = true;
    }
    async loadAtlasLocalClient(logger) {
        // If we've tried and failed to load the Atlas Local client before, don't try again
        if (!this.isAtlasLocalSupported) {
            return undefined;
        }
        try {
            // Try to dynamically import the Atlas Local client library - this will fail
            // on unsupported platforms (e.g., Windows on ARM)
            const { Client: AtlasLocalClient } = await Promise.resolve().then(() => __importStar(require("@mongodb-js/atlas-local")));
            return AtlasLocalClient;
        }
        catch {
            this.isAtlasLocalSupported = false;
            logger.warning({
                id: index_js_1.LogId.atlasLocalUnsupportedPlatform,
                message: "Atlas Local is not supported on this platform. Atlas Local tools are disabled. All other tools continue to work normally.",
                context: "Atlas Local Initialization",
            });
            return undefined;
        }
    }
}
DefaultLibraryLoader.instance = new DefaultLibraryLoader();
const defaultCreateAtlasLocalClient = async ({ logger, loader }) => {
    const libraryLoader = loader ?? DefaultLibraryLoader.instance;
    const client = await libraryLoader.loadAtlasLocalClient(logger);
    try {
        // Connect to Atlas Local client
        // This will fail if docker is not running
        return client?.connect();
    }
    catch {
        logger.warning({
            id: index_js_1.LogId.atlasLocalDockerNotRunning,
            message: "Cannot connect to Docker. Atlas Local tools are disabled. All other tools continue to work normally.",
            context: "Atlas Local Initialization",
        });
        return undefined;
    }
};
exports.defaultCreateAtlasLocalClient = defaultCreateAtlasLocalClient;
//# sourceMappingURL=atlasLocal.js.map