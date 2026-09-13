import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const srcRoot = dirname(fileURLToPath(import.meta.url));

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      return walk(path);
    }
    if (entry.name.includes('.test.')) {
      return [];
    }
    return entry.name.endsWith('.ts') || entry.name.endsWith('.tsx') || entry.name.endsWith('.css')
      ? [path]
      : [];
  });
}

describe('frontend source hygiene', () => {
  const files = walk(srcRoot);
  const combined = files.map((file) => readFileSync(file, 'utf8')).join('\n');

  it('does not embed secrets, tokens or Spider/Icatu clients', () => {
    expect(combined).not.toMatch(/Bearer\s+[A-Za-z0-9\-._~+/]+=*/);
    expect(combined).not.toMatch(/localStorage/);
    expect(combined).not.toMatch(/sessionStorage/);
    expect(combined).not.toMatch(/document\.cookie/);
    expect(combined).not.toContain('Authorization:');
    expect(combined.toLowerCase()).not.toContain('spider.local');
    expect(combined.toLowerCase()).not.toContain('icatu.local');
    expect(combined).not.toMatch(/fetch\([^)]*icatu/i);
    expect(combined).not.toContain('client_secret');
    expect(combined).not.toContain('SatelliteContract');
  });

  it('does not fake Spider or mock progress with timers', () => {
    const mvp = readFileSync(join(srcRoot, 'demonstration', 'IntegratedMvpPage.tsx'), 'utf8');
    expect(mvp).not.toMatch(/setTimeout/);
    expect(mvp).not.toMatch(/Em análise na Spider/);
  });

  it('does not introduce unsafe HTML, analytics or external fonts', () => {
    expect(combined).not.toContain('dangerouslySetInnerHTML');
    expect(combined).not.toContain('fonts.googleapis.com');
    expect(combined).not.toContain('google-analytics');
    expect(combined).not.toContain('googletagmanager');
  });

  it('imports the official logo file', () => {
    expect(combined).toContain("from '../../images/segsense logo.png'");
  });
});
