/**
 * Adendo global de linguagem: inglês não consagrado não entra na superfície.
 * Contratos, códigos públicos e auditoria recolhida ficam de fora.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_SURFACE_ENGLISH,
  SURFACE_ENUM_LABEL,
  SURFACE_PHRASES,
  isContractToken,
} from "./language/surface";

const SRC = __dirname;
const SURFACE_DIRS = ["pages", "components", "fluxo", "costing", "guide", "ops", "assistant", "editorial", "language"];
const SKIP_FILES = new Set(["surface.ts", "surface-language.test.ts"]);

function walk(dir: string): string[] {
  if (!statSync(dir, { throwIfNoEntry: false })?.isDirectory()) return [];
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) out.push(...walk(path));
    else if (/\.(tsx|ts)$/.test(name) && !name.includes(".test.") && !SKIP_FILES.has(name)) {
      out.push(path);
    }
  }
  return out;
}

function quotedStrings(source: string): Array<{ raw: string; staticText: string }> {
  const found: Array<{ raw: string; staticText: string }> = [];
  const re = /(['"`])((?:\\.|(?!\1).)*)\1/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(source))) {
    const quote = match[1];
    const raw = match[2].replace(/\\n/g, " ").replace(/\\"/g, '"');
    const staticText = quote === "`" ? raw.replace(/\$\{[^}]*\}/g, " ") : raw;
    found.push({ raw, staticText });
  }
  return found;
}

function isCssClassList(value: string): boolean {
  return /^(?:[a-z][a-z0-9_-]*)(?:\s+[a-z][a-z0-9_-]*)*$/.test(value.trim());
}

function isUiCopy(staticText: string): boolean {
  const text = staticText.trim();
  if (!text) return false;
  if (text.startsWith("/") || text.startsWith("http") || text.startsWith(".")) return false;
  if (text.includes("--") || text.includes("__")) return false;
  if (text.includes("|") && text.includes("\\b")) return false;
  if (isContractToken(text)) return false;
  if (isCssClassList(text)) return false;
  if (/^[a-z]+\.[a-z.]+$/.test(text)) return false;
  if (!/\s/.test(text) && /^[a-z][a-z0-9_-]*[:/=]/.test(text)) return false;
  return /[A-Za-zÀ-ÿ]/.test(text);
}

describe("adendo global de linguagem — superfície", () => {
  it("guarda a frase obrigatória de movimentações", () => {
    expect(SURFACE_PHRASES.movementsImmutable).toBe(
      "Movimentações confirmadas não podem ser editadas. Para corrigir um lançamento, registre uma reversão.",
    );
    expect(SURFACE_PHRASES.movementsImmutable).not.toMatch(/append-only/i);
  });

  it("traduz os tokens do adendo", () => {
    expect(SURFACE_ENUM_LABEL.morning).toBe("Manhã");
    expect(SURFACE_ENUM_LABEL.afternoon).toBe("Tarde");
    expect(SURFACE_ENUM_LABEL.night).toBe("Noite");
    expect(SURFACE_ENUM_LABEL.planned).toBe("Planejada");
    expect(SURFACE_ENUM_LABEL.released).toBe("Liberada");
    expect(SURFACE_ENUM_LABEL.ready).toBe("Pronta");
    expect(SURFACE_ENUM_LABEL["in progress"]).toBe("Em execução");
    expect(SURFACE_ENUM_LABEL.completed).toBe("Concluída");
    expect(SURFACE_ENUM_LABEL.blocked).toBe("Bloqueada");
    expect(SURFACE_ENUM_LABEL.active).toBe("Ativo");
    expect(SURFACE_ENUM_LABEL.inactive).toBe("Inativo");
    expect(SURFACE_ENUM_LABEL.missing).toBe("Ausente");
    expect(SURFACE_ENUM_LABEL.backend).toBe("servidor");
    expect(SURFACE_ENUM_LABEL.frontend).toBe("tela");
    expect(SURFACE_ENUM_LABEL.payload).toBe("conteúdo");
    expect(SURFACE_ENUM_LABEL.source).toBe("Fonte");
  });

  it("reconhece as frases que o adendo mandou sair", () => {
    for (const phrase of [
      "Histórico append-only. Erro se corrige com reversão, nunca com edição.",
      "Observações append-only (mais recente primeiro)",
      "Ler o histórico append-only de movimentos.",
      "A outra métrica é derivada no backend com arredondamento comercial.",
      "memória de cálculo do backend.",
    ]) {
      expect(phrase.match(FORBIDDEN_SURFACE_ENGLISH), phrase).toBeTruthy();
    }
  });

  it("impede regressão de inglês não consagrado em cópia visível", () => {
    const files = SURFACE_DIRS.flatMap((name) => walk(join(SRC, name)));
    const leaks: string[] = [];
    for (const path of files) {
      const rel = relative(SRC, path).replaceAll("\\", "/");
      const text = readFileSync(path, "utf8");
      for (const { raw, staticText } of quotedStrings(text)) {
        if (!isUiCopy(staticText)) continue;
        const hit = staticText.match(FORBIDDEN_SURFACE_ENGLISH);
        if (hit) leaks.push(`${rel}: “${raw.slice(0, 120)}” → ${hit[0]}`);
      }
    }
    expect(leaks, leaks.join("\n")).toEqual([]);
  });
});
