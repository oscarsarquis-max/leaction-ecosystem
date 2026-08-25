package br.com.banco.spider.operational.failurelab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class FailureLabCatalogLoaderTest {

  private final FailureLabCatalogLoader loader =
      new FailureLabCatalogLoader(new ObjectMapper().findAndRegisterModules());

  private static final int MINIMUM_SCENARIOS = 17;

  @Test
  void loadsAtLeastTheMinimumScenarioSet() {
    assertTrue(
        loader.scenarios().size() >= MINIMUM_SCENARIOS,
        "catálogo deve declarar ao menos "
            + MINIMUM_SCENARIOS
            + " cenários, encontrado "
            + loader.scenarios().size());
  }

  @Test
  void publishesEveryCapacityResilienceScenarioWithItsRunbook() {
    List<String> expected =
        List.of(
            "CAPACITY_BULKHEAD_SATURATION",
            "CAPACITY_BACKLOG_HARD_LIMIT",
            "CAPACITY_CIRCUIT_OPEN_RECOVER",
            "CAPACITY_QUOTA_EXHAUSTION",
            "CAPACITY_LOAD_SHEDDING");
    for (String code : expected) {
      FailureScenarioDefinition scenario =
          loader.findScenario(code, "1.0").orElseThrow(() -> new AssertionError("ausente: " + code));
      assertEquals(FailureScenarioCategory.CAPACITY_RESILIENCE, scenario.category());
      assertEquals("runbook:failure-lab:capacity@1.0", scenario.runbookRef());
      assertTrue(loader.findRunbook(scenario.runbookRef()).isPresent());
    }
  }

  @Test
  void publishesRetryThenSuccessAtVersionOne() {
    Optional<FailureScenarioDefinition> scenario =
        loader.findScenario("RETRY_THEN_SUCCESS", "1.0");
    assertTrue(scenario.isPresent());
    assertEquals("1.0", scenario.get().version());
    assertEquals("RETRY_THEN_SUCCESS@1.0", scenario.get().ref());
    assertTrue(
        scenario.get().expectedObservations().stream()
            .anyMatch(observation -> observation.code().equals("AT_LEAST_TWO_ATTEMPTS")));
  }

  @Test
  void rejectsScenarioLookupWithMismatchedVersion() {
    assertTrue(loader.findScenario("RETRY_THEN_SUCCESS", "9.9").isEmpty());
    assertTrue(loader.findScenario("DOES_NOT_EXIST", null).isEmpty());
  }

  @Test
  void everyScenarioResolvesAPublishedRunbook() {
    for (FailureScenarioDefinition scenario : loader.scenarios()) {
      Optional<MockOperationalRunbook> runbook = loader.findRunbook(scenario.runbookRef());
      assertTrue(
          runbook.isPresent(),
          "cenário " + scenario.code() + " referencia runbook desconhecido " + scenario.runbookRef());
      assertNotNull(runbook.get().title());
    }
  }

  @Test
  void everyScenarioStaysInsideTheMockOnlyBoundary() {
    for (FailureScenarioDefinition scenario : loader.scenarios()) {
      assertEquals(
          FailureScenarioDefinition.MOCK_ONLY,
          scenario.targetBoundary(),
          "cenário " + scenario.code() + " fora da fronteira MOCK_ONLY");
    }
  }

  @Test
  void boundaryOtherThanMockOnlyIsRejectedAtConstruction() {
    IllegalArgumentException rejected =
        assertThrows(
            IllegalArgumentException.class,
            () ->
                new FailureScenarioDefinition(
                    1,
                    "PRODUCTION_LIKE",
                    "1.0",
                    "Cenário inválido",
                    "",
                    FailureScenarioCategory.EXECUTION,
                    "PRODUCTION",
                    List.of(),
                    List.of(),
                    List.of(
                        new ExpectedObservation(
                            "NO_SECRET_EXPOSED",
                            "",
                            "FAILURE_LAB_RUN",
                            ObservationPredicateType.NO_SECRET_EXPOSED,
                            "true",
                            true)),
                    Duration.ofMinutes(1),
                    1,
                    "runbook:failure-lab:retry@1.0",
                    null,
                    null));
    assertTrue(rejected.getMessage().contains("MOCK_ONLY"));
  }
}
