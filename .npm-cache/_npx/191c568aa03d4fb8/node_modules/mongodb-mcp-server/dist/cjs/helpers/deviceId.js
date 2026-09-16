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
exports.DeviceId = exports.DEVICE_ID_TIMEOUT = void 0;
const device_id_1 = require("@mongodb-js/device-id");
const index_js_1 = require("../common/logging/index.js");
exports.DEVICE_ID_TIMEOUT = 3000;
class DeviceId {
    constructor(logger, timeout = exports.DEVICE_ID_TIMEOUT) {
        this.logger = logger;
        this.timeout = timeout;
        this.getMachineId = async () => {
            const nodeMachineId = await Promise.resolve().then(() => __importStar(require("node-machine-id")));
            const machineId = nodeMachineId.default?.machineId || nodeMachineId.machineId;
            return machineId(true);
        };
        this.abortController = new AbortController();
        this.deviceIdPromise = DeviceId.UnknownDeviceId;
    }
    initialize() {
        this.deviceIdPromise = (0, device_id_1.getDeviceId)({
            getMachineId: this.getMachineId,
            onError: (reason, error) => {
                this.handleDeviceIdError(reason, String(error));
            },
            timeout: this.timeout,
            abortSignal: this.abortController.signal,
        });
    }
    static create(logger, timeout) {
        const instance = new DeviceId(logger, timeout ?? exports.DEVICE_ID_TIMEOUT);
        instance.initialize();
        return instance;
    }
    /**
     * Closes the device ID calculation promise and abort controller.
     */
    close() {
        this.abortController.abort();
    }
    /**
     * Gets the device ID, waiting for the calculation to complete if necessary.
     * @returns Promise that resolves to the device ID string
     */
    get() {
        return this.deviceIdPromise;
    }
    handleDeviceIdError(reason, error) {
        this.deviceIdPromise = DeviceId.UnknownDeviceId;
        switch (reason) {
            case "resolutionError":
                this.logger.debug({
                    id: index_js_1.LogId.deviceIdResolutionError,
                    context: "deviceId",
                    message: `Resolution error: ${String(error)}`,
                });
                break;
            case "timeout":
                this.logger.debug({
                    id: index_js_1.LogId.deviceIdTimeout,
                    context: "deviceId",
                    message: "Device ID retrieval timed out",
                    noRedaction: true,
                });
                break;
            case "abort":
                // No need to log in the case of 'abort' errors
                break;
        }
    }
}
exports.DeviceId = DeviceId;
DeviceId.UnknownDeviceId = Promise.resolve("unknown");
//# sourceMappingURL=deviceId.js.map