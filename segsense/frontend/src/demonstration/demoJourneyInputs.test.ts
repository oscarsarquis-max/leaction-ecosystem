import { describe, expect, it } from 'vitest';
import { dwellingTypeLabel, publicQuoteExplanation } from './demoJourneyInputs';

describe('public quote copy', () => {
  it('maps dwelling codes to business language', () => {
    expect(dwellingTypeLabel('APARTMENT')).toBe('apartamento');
    expect(dwellingTypeLabel('HOUSE')).toBe('casa');
    expect(dwellingTypeLabel('OTHER')).toBeNull();
  });

  it('derives the public explanation from persisted quote fields', () => {
    const text = publicQuoteExplanation({
      premiumAnnualCents: 54000,
      insuredAmountCents: 30000000,
      coverPeriodMonths: 12,
      dwellingType: 'APARTMENT',
    });
    expect(text).toMatch(/valor de proteção de R\$\s*300.000,00/);
    expect(text).toMatch(/tipo de imóvel apartamento/);
    expect(text).toMatch(/período de 12 meses/);
    expect(text).toMatch(/prêmio anual simulado de R\$\s*540,00/);
    expect(text).not.toMatch(/bps|APARTMENT|30000000|54000/);
  });

  it('does not invent an explanation without complete fields', () => {
    expect(
      publicQuoteExplanation({
        premiumAnnualCents: 54000,
        dwellingType: 'APARTMENT',
      }),
    ).toBeNull();
  });
});
