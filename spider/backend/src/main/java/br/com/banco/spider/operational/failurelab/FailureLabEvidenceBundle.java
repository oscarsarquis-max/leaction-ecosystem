package br.com.banco.spider.operational.failurelab;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

/** Pacote de evidência segura de uma execução do Failure Lab. */
public record FailureLabEvidenceBundle(
    int schemaVersion,
    String evidenceId,
    String labRunId,
    String scenarioRef,
    String boundary,
    Instant generatedAt,
    List<String> executionRefs,
    List<VerificationResult> verificationResults,
    String redactionStatus,
    String completenessStatus,
    String digest) {

  public static final int SCHEMA_VERSION = 1;
  public static final String REDACTION_APPLIED = "APPLIED";
  public static final String COMPLETE = "COMPLETE";
  public static final String PARTIAL = "PARTIAL";

  public FailureLabEvidenceBundle {
    Objects.requireNonNull(evidenceId, "evidenceId");
    Objects.requireNonNull(labRunId, "labRunId");
    Objects.requireNonNull(scenarioRef, "scenarioRef");
    Objects.requireNonNull(generatedAt, "generatedAt");
    Objects.requireNonNull(digest, "digest");
    if (schemaVersion != SCHEMA_VERSION) {
      throw new IllegalArgumentException("Only schemaVersion 1 is supported");
    }
    boundary = boundary == null ? FailureScenarioDefinition.MOCK_ONLY : boundary;
    executionRefs = executionRefs == null ? List.of() : List.copyOf(executionRefs);
    verificationResults =
        verificationResults == null ? List.of() : List.copyOf(verificationResults);
    redactionStatus = REDACTION_APPLIED;
    completenessStatus = completenessStatus == null ? PARTIAL : completenessStatus;
  }
}
