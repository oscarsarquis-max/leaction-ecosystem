package br.com.banco.spider.implementation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

class Roadmap015026ContractFreezeTest {

  private final ImplementationManifestLoader loader =
      new ImplementationManifestLoader(new ObjectMapper().findAndRegisterModules());

  @Test
  void freezesOfficialRoadmapFieldsAgainstContract() {
    var m = loader.loadAndValidate();
    assertEquals("GROUP_A_VISIBILITY_OBSERVABILITY", m.currentGroup());
    assertEquals("SPIDER-PROMPT-017", m.currentPrompt());

    Map<String, ImplementationCapability> journey =
        m.capabilities().stream()
            .filter(c -> c.promptRef().compareTo("SPIDER-PROMPT-015") >= 0)
            .collect(Collectors.toMap(ImplementationCapability::promptRef, c -> c));

    assertEquals(12, journey.size());
    assertEquals("VERIFIED", journey.get("SPIDER-PROMPT-015").status());
    assertEquals("VERIFIED", journey.get("SPIDER-PROMPT-016").status());
    assertEquals("OFF_BY_DEFAULT", journey.get("SPIDER-PROMPT-016").runtimeAvailability());
    assertEquals(
        "GROUP_A_VISIBILITY_OBSERVABILITY", journey.get("SPIDER-PROMPT-016").groupCode());
    assertEquals(
        "Telemetria Canônica e Operational Events", journey.get("SPIDER-PROMPT-016").title());
    assertEquals(List.of("CAP-015"), journey.get("SPIDER-PROMPT-016").dependencies());
    assertEquals("VERIFIED", journey.get("SPIDER-PROMPT-017").status());
    assertEquals("OFF_BY_DEFAULT", journey.get("SPIDER-PROMPT-017").runtimeAvailability());

    assertEquals(
        "SDK da Porta Universal e Kit de Certificação de Adapters",
        journey.get("SPIDER-PROMPT-023").title());
    assertFalse(
        journey.get("SPIDER-PROMPT-023").title().toLowerCase().contains("legacy endpoint"));

    assertEquals(
        "Primeiro Legado Real, Canary e Migração Controlada",
        journey.get("SPIDER-PROMPT-026").title());
    assertFalse(
        journey.get("SPIDER-PROMPT-026").title().toLowerCase().contains("production cutover"));
    assertEquals("REAL_PILOT", journey.get("SPIDER-PROMPT-026").integrationLevel());
    assertTrue(journey.values().stream().noneMatch(c -> "PRODUCTION".equals(c.integrationLevel())));

    assertEquals("CORPORATE_SANDBOX", journey.get("SPIDER-PROMPT-025").integrationLevel());
    assertEquals("PLANNED", journey.get("SPIDER-PROMPT-025").status());
    assertEquals("NOT_IMPLEMENTED", journey.get("SPIDER-PROMPT-025").runtimeAvailability());

    long aVerified =
        journey.values().stream()
            .filter(c -> "GROUP_A_VISIBILITY_OBSERVABILITY".equals(c.groupCode()))
            .filter(c -> "VERIFIED".equals(c.status()))
            .count();
    long aPlanned =
        journey.values().stream()
            .filter(c -> "GROUP_A_VISIBILITY_OBSERVABILITY".equals(c.groupCode()))
            .filter(c -> "PLANNED".equals(c.status()))
            .count();
    assertEquals(3, aVerified);
    assertEquals(1, aPlanned);

    assertEquals(List.of("CAP-018"), journey.get("SPIDER-PROMPT-019").dependencies());
    assertEquals(List.of("CAP-021"), journey.get("SPIDER-PROMPT-022").dependencies());
    assertEquals(List.of("CAP-024"), journey.get("SPIDER-PROMPT-025").dependencies());
    assertEquals(List.of("CAP-025"), journey.get("SPIDER-PROMPT-026").dependencies());
  }
}
