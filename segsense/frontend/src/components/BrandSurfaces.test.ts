import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const srcRoot = dirname(fileURLToPath(import.meta.url));
const images = join(srcRoot, '..', '..', 'images');

describe('SegSense brand surfaces', () => {
  const official = join(images, 'segsense logo.png');
  const header = join(images, 'segsense-logo-header.png');
  const tokens = readFileSync(join(srcRoot, '../styles/tokens.css'), 'utf8');
  const indexCss = readFileSync(join(srcRoot, '../index.css'), 'utf8');
  const homeCss = readFileSync(join(srcRoot, '../public/home.css'), 'utf8');
  const demoCss = readFileSync(join(srcRoot, '../demonstration/demonstration.css'), 'utf8');
  const mvpCss = readFileSync(join(srcRoot, '../demonstration/integrated-mvp.css'), 'utf8');
  const logo = readFileSync(join(srcRoot, 'SegSenseLogo.tsx'), 'utf8');

  it('preserves the official PNG byte-for-byte', () => {
    const digest = createHash('sha256').update(readFileSync(official)).digest('hex').toUpperCase();
    expect(digest).toBe('CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D');
  });

  it('displays the header crop derived from transparent margins only', () => {
    expect(logo).toContain("from '../../images/segsense-logo-header.png'");
    expect(logo).not.toContain("from '../../images/segsense logo.png'");
    const derived = readFileSync(header);
    expect(derived.length).toBeGreaterThan(1000);
    expect(createHash('sha256').update(derived).digest('hex').toUpperCase()).not.toBe(
      'CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D',
    );
  });

  it('sizes the mark by surface without a crushing global override', () => {
    expect(tokens).toContain('--segsense-admin-logo: 3.75rem');
    expect(tokens).toContain('--segsense-home-logo: 5rem');
    expect(tokens).toContain('--segsense-demo-logo: 6.25rem');
    expect(tokens).toContain('--segsense-public-logo: clamp(6.5rem, 20vw, 8.5rem)');
    expect(indexCss).toContain('height: var(--segsense-admin-logo)');
    expect(indexCss).toContain('height: var(--segsense-public-logo)');
    expect(indexCss).not.toMatch(/\.brand-logo--admin\s*\{[^}]*width:\s*var\(--segsense-admin-logo\)/);
    expect(homeCss).toContain('height: var(--segsense-home-logo)');
    expect(homeCss).not.toMatch(/\.home-page \.brand-logo--public \{\s*width: 4\.5rem;\s*height: 4\.5rem/);
    expect(demoCss).toContain('height: var(--segsense-demo-logo)');
    expect(mvpCss).toContain('max-height: none');
    expect(mvpCss).not.toContain('max-height: 2.4rem');
    expect(`${indexCss}\n${homeCss}\n${demoCss}\n${mvpCss}`).not.toMatch(/transform:\s*scale\(/);
  });
});
