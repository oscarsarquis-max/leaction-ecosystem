/**
 * Scanner contextual R026-004-d — localiza candidatos; não altera automaticamente.
 * Decisão final é humana: códigos públicos e termos científicos legítimos são permitidos.
 */
import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "pages");
const OPS = join(__dirname, "ops");
const OUT = join(__dirname, "..", "..", "documentacao", "evidencias", "cursor-026", "revisao-proprietario");

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi;
const HASH_RE = /\b[0-9a-f]{32,64}\b/gi;
const EVENT_RE = /\b[a-z]+\.[a-z_]+\b/g;
const NULLISH_RE = /\b(null|undefined)\b/g;
const JSON_RE = /JSON\.stringify\(/g;
const DECIMAL_RE = /\d+\.\d{4,}/g;
const INFRA_RE = /\b(OIDC|PKCE|RLS|Bedrock|ledger|payload|snapshot_hash|row_version)\b/gi;

const ALLOWED_PUBLIC_CODE = /\b(ORD|OP|PLN|LOT|PICK|CNT|RPL|CMD)-[A-Z0-9-]+\b/;

type Finding = {
  file: string;
  kind: string;
  sample: string;
  line: number;
};

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) out.push(...walk(path));
    else if (/\.(tsx|ts)$/.test(name) && !name.includes(".test.")) out.push(path);
  }
  return out;
}

function scanFile(path: string): Finding[] {
  const text = readFileSync(path, "utf8");
  const lines = text.split(/\r?\n/);
  const findings: Finding[] = [];
  const file = relative(join(__dirname, ".."), path).replaceAll("\\", "/");

  lines.forEach((line, index) => {
    if (line.trimStart().startsWith("//") || line.trimStart().startsWith("*")) return;
    // Ignore imports and type-only technical fields in TS types usage for API mapping
    if (line.includes("from ") || line.includes("import ")) return;

    const push = (kind: string, re: RegExp) => {
      const matches = line.match(re);
      if (!matches) return;
      for (const sample of matches) {
        if (ALLOWED_PUBLIC_CODE.test(sample)) continue;
        if (kind === "enum_underscore" && ["display_name", "public_code", "unit_code", "created_at"].includes(sample)) {
          continue;
        }
        findings.push({ file, kind, sample, line: index + 1 });
      }
    };

    push("uuid", UUID_RE);
    push("hash", HASH_RE);
    push("event_dot", EVENT_RE);
    push("nullish_literal", NULLISH_RE);
    push("json_stringify", JSON_RE);
    push("excess_decimal", DECIMAL_RE);
    push("infra_term", INFRA_RE);
    // enums with underscore in string literals only
    const literals = line.match(/["'`][a-z]+(?:_[a-z0-9]+){1,}["'`]/g);
    if (literals) {
      for (const lit of literals) {
        const sample = lit.slice(1, -1);
        if (["display_name", "public_code", "unit_code", "created_at", "row_version"].includes(sample)) continue;
        findings.push({ file, kind: "enum_literal", sample, line: index + 1 });
      }
    }
  });

  return findings;
}

describe("R026-004-d scanner contextual", () => {
  it("gera relatório de candidatos sem falhar a suíte", () => {
    const files = [...walk(ROOT), ...walk(OPS)];
    const all = files.flatMap(scanFile);
    mkdirSync(OUT, { recursive: true });
    const byFile = new Map<string, Finding[]>();
    for (const item of all) {
      const list = byFile.get(item.file) ?? [];
      list.push(item);
      byFile.set(item.file, list);
    }
    const lines = [
      "# Scanner contextual R026-004-d",
      "",
      "Candidatos apenas — revisão humana obrigatória. Códigos públicos válidos são filtrados.",
      "",
      `Arquivos varridos: ${files.length}`,
      `Candidatos: ${all.length}`,
      "",
    ];
    for (const [file, items] of [...byFile.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      lines.push(`## ${file}`);
      for (const item of items.slice(0, 40)) {
        lines.push(`- L${item.line} · ${item.kind} · \`${item.sample}\``);
      }
      if (items.length > 40) lines.push(`- … +${items.length - 40} omitidos`);
      lines.push("");
    }
    writeFileSync(join(OUT, "R026-004-scanner.md"), lines.join("\n"), "utf8");
    expect(files.length).toBeGreaterThan(10);
    // Scanner não falha a suíte: é inventário.
    expect(all.length).toBeGreaterThanOrEqual(0);
  });
});
