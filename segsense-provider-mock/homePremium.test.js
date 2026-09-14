import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calculateSyntheticHomePremium, RATING_RULE_VERSION } from './homePremium.js';

test('apartment 300000 BRL yields 54000 cents', () => {
  const got = calculateSyntheticHomePremium({
    dwellingType: 'APARTMENT',
    insuredAmountCents: 30_000_000,
    coverPeriodMonths: 12,
  });
  assert.equal(got.ok, true);
  assert.equal(got.premiumAnnualCents, 54_000);
  assert.equal(got.ratingRuleVersion, RATING_RULE_VERSION);
  assert.equal(got.nearbyFiresDidNotAdjustPremium, true);
});

test('house same capital yields a different premium', () => {
  const got = calculateSyntheticHomePremium({
    dwellingType: 'HOUSE',
    insuredAmountCents: 30_000_000,
    coverPeriodMonths: 12,
  });
  assert.equal(got.ok, true);
  assert.equal(got.premiumAnnualCents, 66_000);
});

test('doubling capital changes premium', () => {
  const low = calculateSyntheticHomePremium({
    dwellingType: 'APARTMENT',
    insuredAmountCents: 30_000_000,
    coverPeriodMonths: 12,
  });
  const high = calculateSyntheticHomePremium({
    dwellingType: 'APARTMENT',
    insuredAmountCents: 60_000_000,
    coverPeriodMonths: 12,
  });
  assert.equal(low.premiumAnnualCents, 54_000);
  assert.equal(high.premiumAnnualCents, 108_000);
});

test('rejects below minimum and above maximum', () => {
  assert.equal(
    calculateSyntheticHomePremium({
      dwellingType: 'APARTMENT',
      insuredAmountCents: 4_999_999,
      coverPeriodMonths: 12,
    }).error,
    'INSURED_AMOUNT_TOO_LOW',
  );
  assert.equal(
    calculateSyntheticHomePremium({
      dwellingType: 'APARTMENT',
      insuredAmountCents: 200_000_001,
      coverPeriodMonths: 12,
    }).error,
    'INSURED_AMOUNT_TOO_HIGH',
  );
});

test('rejects invalid dwelling and period', () => {
  assert.equal(
    calculateSyntheticHomePremium({
      dwellingType: 'FARM',
      insuredAmountCents: 30_000_000,
      coverPeriodMonths: 12,
    }).error,
    'INVALID_DWELLING',
  );
  assert.equal(
    calculateSyntheticHomePremium({
      dwellingType: 'APARTMENT',
      insuredAmountCents: 30_000_000,
      coverPeriodMonths: 24,
    }).error,
    'INVALID_PERIOD',
  );
});
