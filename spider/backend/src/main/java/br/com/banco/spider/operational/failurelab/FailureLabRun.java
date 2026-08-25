package br.com.banco.spider.operational.failurelab;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Estado imutável de uma execução controlada do Failure Lab. */
public record FailureLabRun(
    int schemaVersion,
    String labRunId,
    String scenarioCode,
    String scenarioVersion,
    Instant requestedAt,
    String requestedBy,
    Instant startedAt,
    Instant completedAt,
    FailureLabRunStatus status,
    String boundary,
    Map<String, String> parameters,
    List<String> executionRefs,
    List<VerificationResult> verificationResults,
    String evidenceSummary,
    String failureMessage) {

  public static final int SCHEMA_VERSION = 1;

  public FailureLabRun {
    Objects.requireNonNull(labRunId, "labRunId");
    Objects.requireNonNull(scenarioCode, "scenarioCode");
    Objects.requireNonNull(scenarioVersion, "scenarioVersion");
    Objects.requireNonNull(requestedAt, "requestedAt");
    Objects.requireNonNull(status, "status");
    if (schemaVersion != SCHEMA_VERSION) {
      throw new IllegalArgumentException("Only schemaVersion 1 is supported");
    }
    requestedBy = requestedBy == null ? "unknown" : requestedBy;
    boundary = boundary == null ? FailureScenarioDefinition.MOCK_ONLY : boundary;
    if (!FailureScenarioDefinition.MOCK_ONLY.equals(boundary)) {
      throw new IllegalArgumentException("Failure Lab runs are restricted to MOCK_ONLY");
    }
    parameters = parameters == null ? Map.of() : Map.copyOf(parameters);
    executionRefs = executionRefs == null ? List.of() : List.copyOf(executionRefs);
    verificationResults =
        verificationResults == null ? List.of() : List.copyOf(verificationResults);
  }

  public static FailureLabRun requested(
      String labRunId,
      FailureScenarioDefinition scenario,
      Map<String, String> parameters,
      String requestedBy,
      Instant requestedAt) {
    return new FailureLabRun(
        SCHEMA_VERSION,
        labRunId,
        scenario.code(),
        scenario.version(),
        requestedAt,
        requestedBy,
        null,
        null,
        FailureLabRunStatus.REQUESTED,
        scenario.targetBoundary(),
        parameters,
        List.of(),
        List.of(),
        null,
        null);
  }

  public FailureLabRun started(Instant startedAt) {
    return new FailureLabRun(
        schemaVersion,
        labRunId,
        scenarioCode,
        scenarioVersion,
        requestedAt,
        requestedBy,
        startedAt,
        completedAt,
        FailureLabRunStatus.RUNNING,
        boundary,
        parameters,
        executionRefs,
        verificationResults,
        evidenceSummary,
        failureMessage);
  }

  public FailureLabRun withStatus(FailureLabRunStatus newStatus) {
    return new FailureLabRun(
        schemaVersion,
        labRunId,
        scenarioCode,
        scenarioVersion,
        requestedAt,
        requestedBy,
        startedAt,
        completedAt,
        newStatus,
        boundary,
        parameters,
        executionRefs,
        verificationResults,
        evidenceSummary,
        failureMessage);
  }

  public FailureLabRun withExecutionRefs(List<String> refs) {
    return new FailureLabRun(
        schemaVersion,
        labRunId,
        scenarioCode,
        scenarioVersion,
        requestedAt,
        requestedBy,
        startedAt,
        completedAt,
        status,
        boundary,
        parameters,
        refs,
        verificationResults,
        evidenceSummary,
        failureMessage);
  }

  public FailureLabRun completed(
      FailureLabRunStatus finalStatus,
      Instant completedAt,
      List<VerificationResult> results,
      String evidenceSummary,
      String failureMessage) {
    return new FailureLabRun(
        schemaVersion,
        labRunId,
        scenarioCode,
        scenarioVersion,
        requestedAt,
        requestedBy,
        startedAt,
        completedAt,
        finalStatus,
        boundary,
        parameters,
        executionRefs,
        results,
        evidenceSummary,
        failureMessage);
  }

  public String scenarioRef() {
    return scenarioCode + "@" + scenarioVersion;
  }
}
