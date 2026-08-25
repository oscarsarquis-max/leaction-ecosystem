package br.com.banco.spider.operational.failurelab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FailureLabEvidenceServiceTest {

  private static final Instant NOW = Instant.parse("2026-01-01T10:00:00Z");

  private final SpiderClock clock = SpiderClock.fixed(NOW);
  private final FailureLabEvidenceService service =
      new FailureLabEvidenceService(clock, IdentifierGenerator.sequential("evidence-test"));

  @Test
  void buildsASafeBundleWithANonBlankDigest() {
    FailureLabEvidenceBundle bundle = service.build(verifiedRun(), scenario());

    assertEquals(FailureLabEvidenceBundle.SCHEMA_VERSION, bundle.schemaVersion());
    assertEquals("labrun-1", bundle.labRunId());
    assertEquals("TEST_SCENARIO@1.0", bundle.scenarioRef());
    assertEquals(FailureScenarioDefinition.MOCK_ONLY, bundle.boundary());
    assertEquals(NOW, bundle.generatedAt());
    assertFalse(bundle.digest().isBlank());
    assertEquals(64, bundle.digest().length());
    assertTrue(bundle.evidenceId().startsWith("labev-"));
  }

  @Test
  void redactionIsAlwaysReportedAsApplied() {
    FailureLabEvidenceBundle bundle = service.build(verifiedRun(), scenario());

    assertEquals(FailureLabEvidenceBundle.REDACTION_APPLIED, bundle.redactionStatus());
    assertEquals("APPLIED", bundle.redactionStatus());
  }

  @Test
  void completenessIsCompleteOnlyWhenNoObservationWasSkipped() {
    FailureLabEvidenceBundle complete = service.build(verifiedRun(), scenario());
    assertEquals(FailureLabEvidenceBundle.COMPLETE, complete.completenessStatus());

    FailureLabRun partialRun =
        verifiedRun()
            .completed(
                FailureLabRunStatus.INCONCLUSIVE,
                NOW,
                List.of(
                    result("EXECUTION_SUCCEEDED", VerificationStatus.PASSED),
                    result("SLI_INSUFFICIENT_DATA", VerificationStatus.NOT_APPLICABLE)),
                "PASSED=1 NOT_APPLICABLE=1",
                null);

    assertEquals(
        FailureLabEvidenceBundle.PARTIAL, service.build(partialRun, scenario()).completenessStatus());
  }

  @Test
  void identicalRunsProduceTheSameDigest() {
    String first = FailureLabEvidenceService.digest(verifiedRun());
    String second = FailureLabEvidenceService.digest(verifiedRun());

    assertEquals(first, second);
    assertEquals(
        service.build(verifiedRun(), scenario()).digest(),
        service.build(verifiedRun(), scenario()).digest());
  }

  @Test
  void digestChangesWhenAnObservationOutcomeChanges() {
    FailureLabRun regressed =
        verifiedRun()
            .completed(
                FailureLabRunStatus.FAILED,
                NOW,
                List.of(
                    result("EXECUTION_SUCCEEDED", VerificationStatus.FAILED),
                    result("NO_SECRET_EXPOSED", VerificationStatus.PASSED)),
                "FAILED=1 PASSED=1",
                null);

    assertNotEquals(
        FailureLabEvidenceService.digest(verifiedRun()),
        FailureLabEvidenceService.digest(regressed));
  }

  private static FailureLabRun verifiedRun() {
    return FailureLabRun.requested("labrun-1", scenario(), Map.of("note", "ok"), "operator", NOW)
        .started(NOW)
        .withExecutionRefs(List.of("exec-1"))
        .completed(
            FailureLabRunStatus.VERIFIED,
            NOW,
            List.of(
                result("EXECUTION_SUCCEEDED", VerificationStatus.PASSED),
                result("NO_SECRET_EXPOSED", VerificationStatus.PASSED)),
            "PASSED=2",
            null);
  }

  private static VerificationResult result(String code, VerificationStatus status) {
    return new VerificationResult(
        code, status, NOW, "true", "true", Map.of("sourceType", "FAILURE_LAB_RUN"), "");
  }

  private static FailureScenarioDefinition scenario() {
    return new FailureScenarioDefinition(
        1,
        "TEST_SCENARIO",
        "1.0",
        "Cenário de teste",
        "Cenário sintético para evidência.",
        FailureScenarioCategory.EXECUTION,
        FailureScenarioDefinition.MOCK_ONLY,
        List.of(),
        List.of("note"),
        List.of(
            new ExpectedObservation(
                "NO_SECRET_EXPOSED",
                "",
                "FAILURE_LAB_RUN",
                ObservationPredicateType.NO_SECRET_EXPOSED,
                "true",
                true)),
        Duration.ofMinutes(2),
        1,
        "runbook:failure-lab:retry@1.0",
        "SUCCESS",
        "TEST_SCENARIO");
  }
}
