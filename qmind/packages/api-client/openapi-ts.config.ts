import { defineConfig } from "@hey-api/openapi-ts";

const outputPath = process.env.QMIND_API_CLIENT_OUT || "src/generated";

/**
 * Source of truth: committed backend OpenAPI freeze (tag openapi-v1-initial).
 * Do not point at a live server — generation must be reproducible offline.
 */
export default defineConfig({
  input: "../../backend/openapi/openapi.json",
  output: {
    path: outputPath,
    lint: false,
    format: false,
  },
  plugins: [
    "@hey-api/typescript",
    {
      name: "@hey-api/sdk",
      asClass: false,
    },
    "@hey-api/client-fetch",
  ],
});
