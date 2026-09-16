"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ListDatabases = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const embeddable_uis_1 = require("@lg-mcp/embeddable-uis");
const hooks_1 = require("@lg-mcp/hooks");
const ListDatabases = () => {
    const { data, isLoading, error, darkMode } = (0, hooks_1.useRenderData)();
    if (isLoading) {
        return (0, jsx_runtime_1.jsx)("div", { children: "Loading..." });
    }
    if (error) {
        return (0, jsx_runtime_1.jsxs)("div", { children: ["Error: ", error] });
    }
    if (!data?.databases) {
        return null;
    }
    return (0, jsx_runtime_1.jsx)(embeddable_uis_1.ListDatabases, { databases: data.databases, darkMode: darkMode });
};
exports.ListDatabases = ListDatabases;
//# sourceMappingURL=ListDatabases.js.map