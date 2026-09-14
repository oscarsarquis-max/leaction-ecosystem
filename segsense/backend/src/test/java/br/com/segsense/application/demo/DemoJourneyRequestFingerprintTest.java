package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import org.junit.jupiter.api.Test;

class DemoJourneyRequestFingerprintTest {

  @Test
  void sameCanonicalRequestHashesEqual() {
    String first =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "UNDERSTAND_PROTECTION_OPTIONS",
            true,
            "",
            "",
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "demo-editorial-v1",
            "family_continuity",
            "continuidade familiar com dependentes");
    String second =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "UNDERSTAND_PROTECTION_OPTIONS",
            true,
            "",
            "",
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "demo-editorial-v1",
            "family_continuity",
            "continuidade familiar com dependentes");
    assertEquals(first, second);
  }

  @Test
  void contextOrIntentionChangeChangesHashWithoutStoringRawText() {
    String family =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "UNDERSTAND_PROTECTION_OPTIONS",
            true,
            "",
            "",
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "demo-editorial-v1",
            "family_continuity",
            "continuidade familiar");
    String income =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "UNDERSTAND_PROTECTION_OPTIONS",
            true,
            "",
            "",
            "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1",
            "demo-income-v1",
            "income_interruption",
            "interrupção de renda");
    String compare =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "COMPARE_COVERAGE_GAPS",
            true,
            "",
            "",
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "demo-editorial-v1",
            "family_continuity",
            "continuidade familiar");
    String quoteAmount =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "SIMULATE_HOME_QUOTE",
            true,
            "",
            "",
            "SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1",
            "demo-fires-v1",
            "nearby_fires",
            "Houve incêndios nas proximidades",
            "SATELLITE_GOVERNED",
            "GOVERNED_SOURCE",
            "APARTMENT",
            "30000000",
            "12");
    String quoteDouble =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            "SIMULATE_HOME_QUOTE",
            true,
            "",
            "",
            "SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1",
            "demo-fires-v1",
            "nearby_fires",
            "Houve incêndios nas proximidades",
            "SATELLITE_GOVERNED",
            "GOVERNED_SOURCE",
            "APARTMENT",
            "60000000",
            "12");
    assertNotEquals(family, income);
    assertNotEquals(family, compare);
    assertNotEquals(quoteAmount, quoteDouble);
    assertEquals(64, family.length());
  }
}
