import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { COMPONENTS, PROTOCOLS, SCHEMA_GROUPS, TABLES, validateDocumentationContent, collectEvidenceRefs } from './index.js';

const spiderRoot = resolve(import.meta.dirname, '../../../..');

describe('snapshot documental', () => {
  it('valida estrutura, relações e fontes', () => {
    const result = validateDocumentationContent();
    expect(result.errors).toEqual([]);
    expect(result.ok).toBe(true);
  });

  it('aponta para arquivos existentes no repositório', () => {
    const missing = collectEvidenceRefs()
      .map((ref) => ref.path)
      .filter((path, index, all) => all.indexOf(path) === index)
      .filter((path) => !path.startsWith('ausência') && !existsSync(resolve(spiderRoot, path)));
    expect(missing).toEqual([]);
  });

  it('cobre o inventário essencial', () => {
    const ids = COMPONENTS.map((c) => c.id);
    ['canonical-http', 'canonical-engine', 'satellite-registry', 'wait-signal', 'callback-outbox', 'monitor-query'].forEach((id) => {
      expect(ids).toContain(id);
    });
    expect(PROTOCOLS.some((p) => p.id === 'satellite-contract')).toBe(true);
    expect(TABLES.some((t) => t.id === 'tb_execution_control' && t.migration)).toBe(true);
    const grouped = SCHEMA_GROUPS.flatMap((g) => g.tables);
    expect(grouped.sort()).toEqual(TABLES.map((t) => t.id).sort());
  });
});
