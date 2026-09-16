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
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ToolBase = exports.MongoDBToolBase = exports.AllTools = void 0;
const AtlasTools = __importStar(require("./atlas/tools.js"));
const AtlasLocalTools = __importStar(require("./atlasLocal/tools.js"));
const MongoDbTools = __importStar(require("./mongodb/tools.js"));
const AssistantTools = __importStar(require("./assistant/tools.js"));
// Export the collection of tools for easier reference
exports.AllTools = Object.values({
    ...MongoDbTools,
    ...AtlasTools,
    ...AtlasLocalTools,
    ...AssistantTools,
});
var mongodbTool_js_1 = require("./mongodb/mongodbTool.js");
Object.defineProperty(exports, "MongoDBToolBase", { enumerable: true, get: function () { return mongodbTool_js_1.MongoDBToolBase; } });
// Export all the individual tools for handpicking
__exportStar(require("./atlas/tools.js"), exports);
__exportStar(require("./atlasLocal/tools.js"), exports);
__exportStar(require("./mongodb/tools.js"), exports);
__exportStar(require("./assistant/tools.js"), exports);
// Export the base tool class and supporting types.
var tool_js_1 = require("./tool.js");
Object.defineProperty(exports, "ToolBase", { enumerable: true, get: function () { return tool_js_1.ToolBase; } });
//# sourceMappingURL=index.js.map