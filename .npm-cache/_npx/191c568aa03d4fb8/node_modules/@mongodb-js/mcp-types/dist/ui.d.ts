export type UIRegistryOptions = {
    customUIs?: (toolName: string) => string | null | Promise<string | null>;
};
export interface IUIRegistry {
    get(toolName: string): Promise<string | null>;
}
//# sourceMappingURL=ui.d.ts.map