package br.com.banco.spider.canonical.contract;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.ResolutionSummary;
import java.util.List;
import java.util.Objects;

/**
 * Resultado canônico imutável. {@code errors} e {@code evidenceRefs} nunca null.
 */
public record CanonicalExecutionResult(
    ContractDescriptor contract,
    ExecutionSummary execution,
    ResultContextReference contextRef,
    ResultTraceDescriptor trace,
    ResolutionSummary resolution,
    CanonicalOutcome outcome,
    List<CanonicalError> errors,
    CallbackDeliverySummary callback,
    List<EvidenceReference> evidenceRefs) {

  public CanonicalExecutionResult {
    Objects.requireNonNull(contract, "contract");
    Objects.requireNonNull(execution, "execution");
    Objects.requireNonNull(contextRef, "contextRef");
    Objects.requireNonNull(trace, "trace");
    errors = errors == null ? List.of() : List.copyOf(errors);
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }

  public ExecutionState state() {
    return execution.state();
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private ContractDescriptor contract;
    private ExecutionSummary execution;
    private ResultContextReference contextRef;
    private ResultTraceDescriptor trace;
    private ResolutionSummary resolution;
    private CanonicalOutcome outcome;
    private List<CanonicalError> errors = List.of();
    private CallbackDeliverySummary callback;
    private List<EvidenceReference> evidenceRefs = List.of();

    public Builder contract(ContractDescriptor contract) {
      this.contract = contract;
      return this;
    }

    public Builder execution(ExecutionSummary execution) {
      this.execution = execution;
      return this;
    }

    public Builder contextRef(ResultContextReference contextRef) {
      this.contextRef = contextRef;
      return this;
    }

    public Builder trace(ResultTraceDescriptor trace) {
      this.trace = trace;
      return this;
    }

    public Builder resolution(ResolutionSummary resolution) {
      this.resolution = resolution;
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

    public Builder callback(CallbackDeliverySummary callback) {
      this.callback = callback;
      return this;
    }

    public Builder evidenceRefs(List<EvidenceReference> evidenceRefs) {
      this.evidenceRefs = evidenceRefs;
      return this;
    }

    public CanonicalExecutionResult build() {
      return new CanonicalExecutionResult(
          contract,
          execution,
          contextRef,
          trace,
          resolution,
          outcome,
          errors,
          callback,
          evidenceRefs);
    }
  }
}
