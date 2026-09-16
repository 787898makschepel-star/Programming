"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectContainerEnv = detectContainerEnv;
const promises_1 = __importDefault(require("fs/promises"));
let containerEnv;
async function detectContainerEnv() {
    if (containerEnv !== undefined) {
        return containerEnv;
    }
    const detect = async function () {
        if (process.platform !== "linux") {
            return false; // we only support linux containers for now
        }
        if (process.env.container) {
            return true;
        }
        const exists = await Promise.all(["/.dockerenv", "/run/.containerenv", "/var/run/.containerenv"].map(async (file) => {
            try {
                await promises_1.default.access(file);
                return true;
            }
            catch {
                return false;
            }
        }));
        return exists.includes(true);
    };
    containerEnv = await detect();
    return containerEnv;
}
//# sourceMappingURL=container.js.map