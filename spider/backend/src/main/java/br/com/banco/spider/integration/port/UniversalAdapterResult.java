package br.com.banco.spider.integration.port;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

/** Resultado universal do Adapter — neutro a transporte. */
public record UniversalAdapterResult(
    String protocolSchemaVersion,
    String protocolVersion,
    String invocationId,
    String executionId,
    String stepId,
    String attemptId,
    Instant startedAt,
    Instant completedAt,
    AdapterDispositionMode dispositionMode,
    CanonicalOutcome outcome,
    List<CanonicalError> errors,
    List<EvidenceReference> evidenceRefs,
    String correlationId,
    ContinuationDescriptor continuation) {

  public UniversalAdapterResult {
    Objects.requireNonNull(invocationId, "invocationId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(dispositionMode, "dispositionMode");
    Objects.requireNonNull(correlationId, "correlationId");
    errors = errors == null ? List.of() : List.copyOf(errors);
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
    if (protocolSchemaVersion == null || protocolSchemaVersion.isBlank()) {
      protocolSchemaVersion = "1.0";
    }
    if (protocolVersion == null || protocolVersion.isBlank()) {
      protocolVersion = "1.0.0";
    }
    if (dispositionMode == AdapterDispositionMode.ACCEPTED_ASYNC && continuation == null) {
      throw new IllegalArgumentException("continuation is required for ACCEPTED_ASYNC");
    }
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private String protocolSchemaVersion = "1.0";
    private String protocolVersion = "1.0.0";
    private String invocationId;
    private String executionId;
    private String stepId;
    private String attemptId;
    private Instant startedAt;
    private Instant completedAt;
    private AdapterDispositionMode dispositionMode;
    private CanonicalOutcome outcome;
    private List<CanonicalError> errors = List.of();
    private List<EvidenceReference> evidenceRefs = List.of();
    private String correlationId;
    private ContinuationDescriptor continuation;

    public Builder invocationId(String invocationId) {
      this.invocationId = invocationId;
      return this;
    }

    public Builder executionId(String executionId) {
      this.executionId = executionId;
      return this;
    }

    public Builder stepId(String stepId) {
      this.stepId = stepId;
      return this;
    }

    public Builder attemptId(String attemptId) {
      this.attemptId = attemptId;
      return this;
    }

    public Builder startedAt(Instant startedAt) {
      this.startedAt = startedAt;
      return this;
    }

    public Builder completedAt(Instant completedAt) {
      this.completedAt = completedAt;
      return this;
    }

    public Builder dispositionMode(AdapterDispositionMode dispositionMode) {
      this.dispositionMode = dispositionMode;
      return this;
    }

    public Builder outcome(CanonicalOutcome outcome) {
      this.outcome = outcome;
      return this;
    }

    public Builder errors(List<CanonicalError> errors) {
      this.errors = errors;
      return this;
    }

    public Builder evidenceRefs(List<EvidenceReference> evidenceRefs) {
      this.evidenceRefs = evidenceRefs;
      return this;
    }

    public Builder correlationId(String correlationId) {
      this.correlationId = correlationId;
      return this;
    }

    public Builder continuation(ContinuationDescriptor continuation) {
      this.continuation = continuation;
      return this;
    }

    public UniversalAdapterResult build() {
      return new UniversalAdapterResult(
          protocolSchemaVersion,
          protocolVersion,
          invocationId,
          executionId,
          stepId,
          attemptId,
          startedAt,
          completedAt,
          dispositionMode,
          outcome,
          errors,
          evidenceRefs,
          correlationId,
          continuation);
    }
  }
}
