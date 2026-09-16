"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.operationWithFallback = operationWithFallback;
async function operationWithFallback(performOperation, fallback) {
    try {
        return await performOperation();
    }
    catch {
        return fallback;
    }
}
//# sourceMappingURL=operationWithFallback.js.map