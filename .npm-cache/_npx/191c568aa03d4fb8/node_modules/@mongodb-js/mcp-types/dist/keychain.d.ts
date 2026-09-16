export interface IKeychain {
    register(options: {
        value: unknown;
        kind: string;
    }): void;
    clearAllSecrets(): void;
    readonly allSecrets: unknown[];
}
//# sourceMappingURL=keychain.d.ts.map