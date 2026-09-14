/**
 * HOME_QUOTE_SYNTHETIC_V1 — invented demo rates, not market, not actuarial, not Icatu.
 *
 * premiumAnnualCents = round_half_up(insuredAmountCents * dwellingBps / 10000)
 * APARTMENT: 18 bps (0.18% a.a.)
 * HOUSE: 22 bps
 * coverPeriodMonths must be 12 (annual premium; period is informational)
 * nearby-fires context does not change the premium
 */

export const RATING_RULE_VERSION = 'HOME_QUOTE_SYNTHETIC_V1';
export const MIN_INSURED_CENTS = 5_000_000;
export const MAX_INSURED_CENTS = 200_000_000;
export const ALLOWED_PERIOD_MONTHS = 12;
export const DWELLING_BPS = Object.freeze({ APARTMENT: 18, HOUSE: 22 });

export function roundHalfUp(numerator, denominator) {
  if (denominator <= 0) {
    throw new Error('denominator');
  }
  const negative = numerator < 0;
  const value = Math.abs(numerator);
  const q = Math.trunc(value / denominator);
  const r = value % denominator;
  const bump = r * 2 >= denominator ? 1 : 0;
  return (negative ? -1 : 1) * (q + bump);
}

export function calculateSyntheticHomePremium(input) {
  const dwellingType = input?.dwellingType;
  const insuredAmountCents = Number(input?.insuredAmountCents);
  const coverPeriodMonths = Number(input?.coverPeriodMonths);
  if (dwellingType !== 'APARTMENT' && dwellingType !== 'HOUSE') {
    return { ok: false, error: 'INVALID_DWELLING' };
  }
  if (!Number.isInteger(insuredAmountCents) || insuredAmountCents < MIN_INSURED_CENTS) {
    return { ok: false, error: 'INSURED_AMOUNT_TOO_LOW' };
  }
  if (insuredAmountCents > MAX_INSURED_CENTS) {
    return { ok: false, error: 'INSURED_AMOUNT_TOO_HIGH' };
  }
  if (coverPeriodMonths !== ALLOWED_PERIOD_MONTHS) {
    return { ok: false, error: 'INVALID_PERIOD' };
  }
  const bps = DWELLING_BPS[dwellingType];
  const premiumAnnualCents = roundHalfUp(insuredAmountCents * bps, 10_000);
  return {
    ok: true,
    ratingRuleVersion: RATING_RULE_VERSION,
    dwellingType,
    insuredAmountCents,
    coverPeriodMonths,
    dwellingBps: bps,
    premiumAnnualCents,
    currency: 'BRL',
    nearbyFiresDidNotAdjustPremium: true,
  };
}
