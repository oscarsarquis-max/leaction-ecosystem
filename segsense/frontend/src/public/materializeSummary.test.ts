import { describe, expect, it } from 'vitest';
import { materializeContextSummary } from './materializeSummary';

describe('materializeContextSummary', () => {
  it('replaces declared placeholders with publisher values as plain text', () => {
    expect(
      materializeContextSummary('Resumo para {{riskType}} no ambiente.', {
        riskType: 'quebra de safra',
      }),
    ).toEqual({ mode: 'materialized', text: 'Resumo para quebra de safra no ambiente.' });
  });

  it('does not leave raw placeholders when a value is missing', () => {
    expect(
      materializeContextSummary('Resumo para {{riskType}} no ambiente.', {}),
    ).toEqual({ mode: 'split' });
  });

  it('keeps hostile markup as inert string content', () => {
    const result = materializeContextSummary('Contexto {{riskType}}', {
      riskType: '<script>alert(1)</script>',
    });
    expect(result).toEqual({
      mode: 'materialized',
      text: 'Contexto <script>alert(1)</script>',
    });
  });
});
