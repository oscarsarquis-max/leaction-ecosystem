package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Set;
import org.junit.jupiter.api.Test;

class AssembleDemoContextTest {

  @Test
  void emptyUrlAndTextDoesNotChooseFamily() {
    SubmitDemoProtectionJourneyUseCase.AssembledContext assembled =
        SubmitDemoProtectionJourneyUseCase.assembleContext("", "", "", Set.of(5178));
    assertEquals("MISSING_CONTEXT", assembled.status());
    assertNull(assembled.source());
  }

  @Test
  void familyNarrativeIsDeclaredNotGovernedFixture() {
    SubmitDemoProtectionJourneyUseCase.AssembledContext assembled =
        SubmitDemoProtectionJourneyUseCase.assembleContext(
            "", "continuidade familiar com dependentes", "", Set.of(5178));
    assertNull(assembled.status());
    assertNull(assembled.source());
    assertEquals("SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1", assembled.scenarioKey());
    assertEquals("USER_DECLARED", assembled.provenanceSourceType());
    assertEquals(1, assembled.contributions().size());
    assertEquals("VISITOR_DECLARED", assembled.contributions().get(0).get("role"));
  }

  @Test
  void urlPlusSameThemeKeepsTwoContributions() {
    SubmitDemoProtectionJourneyUseCase.AssembledContext assembled =
        SubmitDemoProtectionJourneyUseCase.assembleContext(
            "http://127.0.0.1:5178/demonstracao/fontes/continuidade-familiar",
            "continuidade familiar com dependentes",
            "",
            Set.of(5178));
    assertNull(assembled.status());
    assertEquals(2, assembled.contributions().size());
    assertEquals("BOTH", assembled.selectedContribution());
    assertEquals("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1", assembled.scenarioKey());
  }
}
