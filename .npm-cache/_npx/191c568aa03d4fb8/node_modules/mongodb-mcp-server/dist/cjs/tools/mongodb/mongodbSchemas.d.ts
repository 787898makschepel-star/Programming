import z from "zod";
export declare const AnyAggregateStage: z.ZodRecord<z.ZodString, z.ZodUnknown>;
export declare const DB_AGGREGATE_STAGE_OPERATORS: readonly ["$changeStream", "$currentOp", "$documents", "$listLocalSessions", "$queryStats"];
export declare const IndexDirectionSchema: z.ZodUnion<readonly [z.ZodLiteral<1>, z.ZodLiteral<-1>, z.ZodLiteral<"2d">, z.ZodLiteral<"2dsphere">, z.ZodLiteral<"text">, z.ZodLiteral<"geoHaystack">, z.ZodLiteral<"hashed">]>;
export declare const SortDirectionSchema: z.ZodUnion<readonly [z.ZodLiteral<1>, z.ZodLiteral<-1>, z.ZodLiteral<"asc">, z.ZodLiteral<"desc">, z.ZodLiteral<"ascending">, z.ZodLiteral<"descending">, z.ZodObject<{
    $meta: z.ZodString;
}, z.core.$strip>]>;
export declare const modelsSupportingAutoEmbedIndexes: readonly ["voyage-4", "voyage-4-large", "voyage-4-lite", "voyage-code-3"];
export declare const VectorSearchStage: z.ZodObject<{
    $vectorSearch: z.ZodUnion<readonly [z.ZodObject<{
        exact: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
        index: z.ZodString;
        path: z.ZodString;
        numCandidates: z.ZodOptional<z.ZodNumber>;
        limit: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        filter: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
        queryVector: z.ZodArray<z.ZodNumber>;
    }, z.core.$strip>, z.ZodObject<{
        exact: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
        index: z.ZodString;
        path: z.ZodString;
        numCandidates: z.ZodOptional<z.ZodNumber>;
        limit: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
        filter: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
        query: z.ZodObject<{
            text: z.ZodString;
        }, z.core.$strip>;
        model: z.ZodOptional<z.ZodEnum<{
            "voyage-4": "voyage-4";
            "voyage-4-large": "voyage-4-large";
            "voyage-4-lite": "voyage-4-lite";
            "voyage-code-3": "voyage-code-3";
        }>>;
    }, z.core.$strip>]>;
}, z.core.$strip>;
//# sourceMappingURL=mongodbSchemas.d.ts.map