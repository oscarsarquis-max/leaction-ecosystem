/**
 * Fail if committed src/generated drifts from a fresh offline generation.
 * Generates into packages/api-client/.tmp-generated — never mutates committed tree.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
} from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkgRoot = resolve(__dirname, "..");
const committedDir = join(pkgRoot, "src/generated");
const tmpOut = join(pkgRoot, ".tmp-generated");

function walkFiles(dir, base = dir) {
  const out = [];
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      out.push(...walkFiles(p, base));
    } else if (name.endsWith(".ts") || name.endsWith(".json")) {
      out.push(relative(base, p).replaceAll("\\", "/"));
    }
  }
  return out.sort();
}

function hashTree(dir) {
  const files = walkFiles(dir);
  const h = createHash("sha256");
  for (const f of files) {
    if (f === ".openapi-source.json") {
      const stamp = JSON.parse(readFileSync(join(dir, f), "utf8"));
      h.update(f);
      h.update("\0");
      h.update(String(stamp.sha256 || ""));
      h.update("\0");
      continue;
    }
    h.update(f);
    h.update("\0");
    const text = readFileSync(join(dir, f), "utf8").replaceAll("\r\n", "\n");
    h.update(text);
    h.update("\0");
  }
  return { files, digest: h.digest("hex") };
}

if (!existsSync(committedDir) || walkFiles(committedDir).length === 0) {
  console.error("Missing src/generated — run: npm run generate:api-client");
  process.exit(1);
}

rmSync(tmpOut, { recursive: true, force: true });

const gen = spawnSync(process.execPath, [join(pkgRoot, "scripts/generate.mjs")], {
  cwd: pkgRoot,
  stdio: "inherit",
  env: { ...process.env, QMIND_API_CLIENT_OUT: ".tmp-generated" },
});

if (gen.status !== 0) {
  rmSync(tmpOut, { recursive: true, force: true });
  process.exit(gen.status ?? 1);
}

const before = hashTree(committedDir);
const after = hashTree(tmpOut);
rmSync(tmpOut, { recursive: true, force: true });

if (before.digest !== after.digest) {
  console.error("API client drift detected against backend/openapi/openapi.json");
  console.error(`committed=${before.digest.slice(0, 12)} regenerated=${after.digest.slice(0, 12)}`);
  console.error("Fix: npm run generate:api-client && git add packages/api-client/src/generated");
  process.exit(1);
}

console.log(
  `API client in sync (${before.files.length} files, sha256=${before.digest.slice(0, 12)}…)`,
);
