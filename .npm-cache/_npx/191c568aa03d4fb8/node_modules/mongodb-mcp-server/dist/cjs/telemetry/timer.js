"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Timer = void 0;
/**
 * A reusable timer that wraps setTimeout with browser-safe unref support.
 * In Node.js, unref() prevents the timer from keeping the process alive.
 * In browsers (or environments without unref), the call is safely skipped.
 */
class Timer {
    schedule(callback, delayMs) {
        this.cancel();
        this.timerId = setTimeout(callback, delayMs);
        if (typeof this.timerId?.unref === "function") {
            this.timerId.unref();
        }
    }
    cancel() {
        if (this.timerId !== undefined) {
            clearTimeout(this.timerId);
            this.timerId = undefined;
        }
    }
    get isScheduled() {
        return this.timerId !== undefined;
    }
}
exports.Timer = Timer;
//# sourceMappingURL=timer.js.map