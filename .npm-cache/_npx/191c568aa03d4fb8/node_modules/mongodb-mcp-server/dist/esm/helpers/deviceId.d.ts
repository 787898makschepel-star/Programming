import type { IDeviceId } from "@mongodb-js/mcp-types";
import type { LoggerBase } from "../common/logging/index.js";
export declare const DEVICE_ID_TIMEOUT = 3000;
export declare class DeviceId implements IDeviceId {
    private static readonly UnknownDeviceId;
    private deviceIdPromise;
    private abortController;
    private logger;
    private readonly getMachineId;
    private timeout;
    private constructor();
    private initialize;
    static create(logger: LoggerBase, timeout?: number): DeviceId;
    /**
     * Closes the device ID calculation promise and abort controller.
     */
    close(): void;
    /**
     * Gets the device ID, waiting for the calculation to complete if necessary.
     * @returns Promise that resolves to the device ID string
     */
    get(): Promise<string>;
    private handleDeviceIdError;
}
//# sourceMappingURL=deviceId.d.ts.map