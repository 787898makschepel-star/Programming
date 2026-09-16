import { type ReactElement } from "react";
import type { ListDatabasesOutput } from "../../../tools/mongodb/metadata/listDatabases.js";
/**
 * @internal
 */
export type Database = ListDatabasesOutput["databases"][number];
export declare const ListDatabases: () => ReactElement | null;
//# sourceMappingURL=ListDatabases.d.ts.map