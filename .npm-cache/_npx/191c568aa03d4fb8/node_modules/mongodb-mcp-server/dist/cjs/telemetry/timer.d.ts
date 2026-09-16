/**
 * A reusable timer that wraps setTimeout with browser-safe unref support.
 * In Node.js, unref() prevents the timer from keeping the process alive.
 * In browsers (or environments without unref), the call is safely skipped.
 */
export declare class Timer {
    private timerId;
    schedule(callback: () => void, delayMs: number): void;
    cancel(): void;
    get isScheduled(): boolean;
}
//# sourceMappingURL=timer.d.ts.map