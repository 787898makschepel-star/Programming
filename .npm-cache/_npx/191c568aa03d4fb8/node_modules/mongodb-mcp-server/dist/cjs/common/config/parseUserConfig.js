"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultParserOptions = void 0;
exports.parseUserConfig = parseUserConfig;
const arg_parser_1 = require("@mongosh/arg-parser");
const keychain_js_1 = require("../keychain.js");
const userConfig_js_1 = require("./userConfig.js");
const arg_parser_2 = require("@mongosh/arg-parser/arg-parser");
const zod_1 = require("zod");
const levenshteinModule = __importStar(require("ts-levenshtein"));
const levenshtein = levenshteinModule.default;
exports.defaultParserOptions = {
    // This is the name of key that yargs-parser will look up in CLI
    // arguments (--config) and ENV variables (MDB_MCP_CONFIG) to load an
    // initial configuration from.
    config: "config",
    // This helps parse the relevant environment variables.
    envPrefix: "MDB_MCP_",
    configuration: {
        ...arg_parser_2.defaultParserOptions.configuration,
        // To avoid populating `_` with end-of-flag arguments we explicitly
        // populate `--` variable and altogether ignore them later.
        "populate--": true,
    },
};
function parseUserConfig({ args, overrides, parserOptions = exports.defaultParserOptions, }) {
    const schema = overrides
        ? zod_1.z.object({
            ...userConfig_js_1.UserConfigSchema.shape,
            ...overrides,
        })
        : userConfig_js_1.UserConfigSchema;
    const { error: parseError, warnings, parsed } = parseUserConfigSources({ args, schema, parserOptions });
    if (parseError) {
        return { error: parseError, warnings, parsed: undefined };
    }
    if (parsed.nodb) {
        return {
            error: "Error: The --nodb argument is not supported in the MCP Server. Please remove it from your configuration.",
            warnings,
            parsed: undefined,
        };
    }
    // If we have a connectionSpecifier, which can only appear as the positional
    // argument, then that has to be used on priority to construct the
    // connection string. In this case, if there is a connection string provided
    // by the env variable or config file, that will be overridden.
    const { connectionSpecifier } = parsed;
    if (connectionSpecifier) {
        const connectionInfo = (0, arg_parser_1.generateConnectionInfoFromCliArgs)({ ...parsed, connectionSpecifier });
        parsed.connectionString = connectionInfo.connectionString;
    }
    const configParseResult = schema.safeParse(parsed);
    const mongoshArguments = arg_parser_2.CliOptionsSchema.safeParse(parsed);
    const error = configParseResult.error || mongoshArguments.error;
    if (error) {
        return {
            error: `Invalid configuration for the following fields:\n${error.issues.map((issue) => `${issue.path.join(".")} - ${issue.message}`).join("\n")}`,
            warnings,
            parsed: undefined,
        };
    }
    // TODO: Separate correctly parsed user config from all other valid
    // arguments relevant to mongosh's args-parser.
    const userConfig = { ...parsed, ...configParseResult.data };
    registerKnownSecretsInRootKeychain(userConfig);
    return {
        parsed: userConfig,
        warnings,
        error: undefined,
    };
}
function parseUserConfigSources({ args, schema = userConfig_js_1.UserConfigSchema, parserOptions, }) {
    let parsed;
    let deprecated;
    try {
        const { parsed: parsedResult, deprecated: deprecatedResult } = (0, arg_parser_2.createParseArgsWithCliOptions)({
            schema,
            parserOptions,
        })({
            args,
        });
        parsed = parsedResult;
        deprecated = deprecatedResult;
        // Delete fileNames - this is a field populated by mongosh but not used by us.
        delete parsed.fileNames;
    }
    catch (error) {
        let errorMessage;
        if (error instanceof arg_parser_2.UnknownArgumentError) {
            const matchingKey = matchingConfigKey(error.argument.replace(/^(--)/, ""));
            if (matchingKey) {
                errorMessage = `Error: Invalid command line argument '${error.argument}'. Did you mean '--${matchingKey}'?`;
            }
            else {
                errorMessage = `Error: Invalid command line argument '${error.argument}'.`;
            }
        }
        return {
            error: errorMessage,
            warnings: [],
            parsed: {},
        };
    }
    const deprecationWarnings = [
        ...getWarnings(parsed, args),
        ...Object.entries(deprecated).map(([deprecated, replacement]) => {
            return `Warning: The --${deprecated} argument is deprecated. Use --${replacement} instead.`;
        }),
    ];
    return {
        error: undefined,
        warnings: deprecationWarnings,
        parsed,
    };
}
function registerKnownSecretsInRootKeychain(userConfig) {
    const keychain = keychain_js_1.Keychain.root;
    const maybeRegister = (value, kind) => {
        if (value) {
            keychain.register(value, kind);
        }
    };
    maybeRegister(userConfig.apiClientId, "user");
    maybeRegister(userConfig.apiClientSecret, "password");
    maybeRegister(userConfig.awsAccessKeyId, "password");
    maybeRegister(userConfig.awsIamSessionToken, "password");
    maybeRegister(userConfig.awsSecretAccessKey, "password");
    maybeRegister(userConfig.awsSessionToken, "password");
    maybeRegister(userConfig.password, "password");
    maybeRegister(userConfig.tlsCAFile, "url");
    maybeRegister(userConfig.tlsCRLFile, "url");
    maybeRegister(userConfig.tlsCertificateKeyFile, "url");
    maybeRegister(userConfig.tlsCertificateKeyFilePassword, "password");
    maybeRegister(userConfig.username, "user");
    maybeRegister(userConfig.voyageApiKey, "password");
    maybeRegister(userConfig.connectionString, "mongodb uri");
}
function matchingConfigKey(key) {
    let minLev = Number.MAX_VALUE;
    let suggestion = undefined;
    for (const validKey of userConfig_js_1.ALL_CONFIG_KEYS) {
        const lev = levenshtein.get(key, validKey);
        // Accepting up to 2 typos and should be better than whatever previous
        // suggestion was.
        if (lev <= 2 && lev < minLev) {
            minLev = lev;
            suggestion = validKey;
        }
    }
    return suggestion;
}
function getWarnings(config, cliArguments) {
    const warnings = [];
    if (cliArguments.find((argument) => argument.startsWith("--connectionString"))) {
        warnings.push("Warning: The --connectionString argument is deprecated. Prefer using the MDB_MCP_CONNECTION_STRING environment variable or the first positional argument for the connection string.");
    }
    return warnings;
}
//# sourceMappingURL=parseUserConfig.js.map