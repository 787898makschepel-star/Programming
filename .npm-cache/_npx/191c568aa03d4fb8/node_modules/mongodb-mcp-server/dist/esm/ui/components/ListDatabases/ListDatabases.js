import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { ListDatabases as LGListDatabases } from "@lg-mcp/embeddable-uis";
import { useRenderData } from "@lg-mcp/hooks";
export const ListDatabases = () => {
    const { data, isLoading, error, darkMode } = useRenderData();
    if (isLoading) {
        return _jsx("div", { children: "Loading..." });
    }
    if (error) {
        return _jsxs("div", { children: ["Error: ", error] });
    }
    if (!data?.databases) {
        return null;
    }
    return _jsx(LGListDatabases, { databases: data.databases, darkMode: darkMode });
};
//# sourceMappingURL=ListDatabases.js.map