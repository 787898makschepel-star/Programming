"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.VectorSearchStage = exports.modelsSupportingAutoEmbedIndexes = exports.SortDirectionSchema = exports.IndexDirectionSchema = exports.DB_AGGREGATE_STAGE_OPERATORS = exports.AnyAggregateStage = void 0;
const zod_1 = __importDefault(require("zod"));
const args_js_1 = require("../args.js");
exports.AnyAggregateStage = (0, args_js_1.zEJSON)();
exports.DB_AGGREGATE_STAGE_OPERATORS = [
    "$changeStream",
    "$currentOp",
    "$documents",
    "$listLocalSessions",
    "$queryStats",
];
// Mirrors mongodb's IndexDirection type. The driver additionally accepts
// arbitrary `number` values, but only 1 and -1 are meaningful in practice -
// constraining to the literals gives the LLM a descriptive JSON Schema and
// catches typos at validation time.
exports.IndexDirectionSchema = zod_1.default.union([
    zod_1.default.literal(1),
    zod_1.default.literal(-1),
    zod_1.default.literal("2d"),
    zod_1.default.literal("2dsphere"),
    zod_1.default.literal("text"),
    zod_1.default.literal("geoHaystack"),
    zod_1.default.literal("hashed"),
]);
// Mirrors mongodb's SortDirection type. Covers every literal the driver accepts,
// plus the `{ $meta: string }` form used for text-score sorting.
exports.SortDirectionSchema = zod_1.default.union([
    zod_1.default.literal(1),
    zod_1.default.literal(-1),
    zod_1.default.literal("asc"),
    zod_1.default.literal("desc"),
    zod_1.default.literal("ascending"),
    zod_1.default.literal("descending"),
    zod_1.default.object({ $meta: zod_1.default.string() }),
]);
const zCommonVectorSearchStageParams = zod_1.default.object({
    exact: zod_1.default
        .boolean()
        .optional()
        .default(false)
        .describe("When true, uses an ENN algorithm, otherwise uses ANN. Using ENN is not compatible with numCandidates, in that case, numCandidates must be left empty."),
    index: zod_1.default.string().describe("Name of the index, as retrieved from the `collection-indexes` tool."),
    path: zod_1.default
        .string()
        .describe("Field, in dot notation, where to search. There must be a vector search index for that field."),
    numCandidates: zod_1.default
        .number()
        .int()
        .positive()
        .optional()
        .describe("Number of candidates for the ANN algorithm. Mandatory when exact is false."),
    limit: zod_1.default.number().int().positive().optional().default(10),
    filter: (0, args_js_1.zEJSON)()
        .optional()
        .describe("MQL filter that can only use filter fields from the index definition. Note to LLM: If unsure, use the `collection-indexes` tool to learn which fields can be used for filtering."),
});
const zClassicVectorSearchStageParams = zCommonVectorSearchStageParams.extend({
    queryVector: zod_1.default
        .array(zod_1.default.number())
        .describe("The vector embeddings to search for when using classic vector search indexes (type: 'vector'). Provide embeddings as an array of numbers. Use this for classic vector indexes. For auto-embed indexes (type: 'autoEmbed'), use 'query' instead."),
});
exports.modelsSupportingAutoEmbedIndexes = [
    "voyage-4",
    "voyage-4-large",
    "voyage-4-lite",
    "voyage-code-3",
];
const zAutoEmbedVectorSearchStageParams = zCommonVectorSearchStageParams.extend({
    query: zod_1.default
        .object({
        text: zod_1.default.string().describe("The text query to search for."),
    })
        .describe("The query to search for when using auto-embed indexes (type: 'autoEmbed'). MongoDB will automatically generate embeddings for the text at query time. Use this for auto-embed indexes, not 'queryVector'."),
    model: zod_1.default
        .enum(exports.modelsSupportingAutoEmbedIndexes)
        .optional()
        .describe("The embedding model to use for generating embeddings from the query text. If not specified, defaults to the model configured in the auto-embed index definition."),
});
exports.VectorSearchStage = zod_1.default.object({
    $vectorSearch: zod_1.default.union([
        zClassicVectorSearchStageParams.describe("Classic vector search using 'queryVector'. Use this when the indexed field has a classic vector index (type: 'vector'). Note to LLM: Use the collection-indexes tool to verify the target field has a classic vector index before using 'queryVector'."),
        zAutoEmbedVectorSearchStageParams.describe("Auto-embed vector search using 'query'. Use this when the indexed field has an auto-embed index (type: 'autoEmbed'). Note to LLM: Use the collection-indexes tool to verify the target field has an auto-embed index before using 'query'."),
    ]),
});
//# sourceMappingURL=mongodbSchemas.js.map