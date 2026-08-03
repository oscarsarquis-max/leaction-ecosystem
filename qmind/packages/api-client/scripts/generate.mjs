/**
 * Reproducible OpenAPI → TypeScript generation.
 * Reads committed openapi.json only (never a live server).
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkgRoot = resolve(__dirname, "..");
const openapiPath = resolve(pkgRoot, "../../backend/openapi/openapi.json");
const outRel = process.env.QMIND_API_CLIENT_OUT || "src/generated";
const generatedDir = resolve(pkgRoot, outRel);
const stampPath = join(generatedDir, ".openapi-source.json");

if (!existsSync(openapiPath)) {
  console.error(`Missing OpenAPI snapshot: ${openapiPath}`);
  process.exit(1);
}

const bytes = readFileSync(openapiPath);
const sha256 = createHash("sha256").update(bytes).digest("hex");

function emptyDir(dir) {
  mkdirSync(dir, { recursive: true });
  for (const name of readdirSync(dir)) {
    rmSync(join(dir, name), { recursive: true, force: true });
  }
}

emptyDir(generatedDir);

const binCandidates = [
  join(pkgRoot, "node_modules", "@hey-api", "openapi-ts", "bin", "index.cjs"),
  join(pkgRoot, "..", "node_modules", "@hey-api", "openapi-ts", "bin", "index.cjs"),
  join(pkgRoot, "..", "..", "node_modules", "@hey-api", "openapi-ts", "bin", "index.cjs"),
];
const bin = binCandidates.find((p) => existsSync(p)) ?? null;

const result = bin
  ? spawnSync(process.execPath, [bin, "-f", "openapi-ts.config.ts"], {
      cwd: pkgRoot,
      stdio: "inherit",
      env: { ...process.env, QMIND_API_CLIENT_OUT: outRel },
    })
  : spawnSync(
      process.platform === "win32" ? "npx.cmd" : "npx",
      ["--no-install", "openapi-ts", "-f", "openapi-ts.config.ts"],
      {
        cwd: pkgRoot,
        stdio: "inherit",
        shell: process.platform === "win32",
        env: { ...process.env, QMIND_API_CLIENT_OUT: outRel },
      },
    );

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

const banner =
  "/* AUTO-GENERATED from qmind/backend/openapi/openapi.json - DO NOT EDIT. Run: npm run generate:api-client */\n";

function stampTsFiles(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      stampTsFiles(p);
      continue;
    }
    if (!name.endsWith(".ts")) continue;
    let text = readFileSync(p, "utf8");
    if (!text.startsWith("/* AUTO-GENERATED")) {
      writeFileSync(p, banner + text, "utf8");
    }
  }
}

stampTsFiles(generatedDir);

writeFileSync(
  stampPath,
  `${JSON.stringify(
    {
      source: "qmind/backend/openapi/openapi.json",
      freezeTag: "openapi-v1-initial",
      sha256,
      generatedAt: new Date().toISOString(),
      generator: "@hey-api/openapi-ts",
    },
    null,
    2,
  )}\n`,
  "utf8",
);

console.log(`Generated @qmind/api-client → ${outRel} (sha256=${sha256.slice(0, 12)}…)`);
