package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.step.StepState;
import java.util.List;

public record ExternalSignalProcessingResult(
    ExternalSignalProcessingStatus processingStatus,
    String executionId,
    ExecutionState executionState,
    StepState stepState,
    CanonicalExecutionResult canonicalExecutionResult,
    CanonicalError error,
    List<EvidenceReference> evidenceRefs) {

  public ExternalSignalProcessingResult {
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }

  public static ExternalSignalProcessingResult of(
      ExternalSignalProcessingStatus status,
      String executionId,
      ExecutionState executionState,
      StepState stepState,
      CanonicalExecutionResult result,
      CanonicalError error) {
    return new ExternalSignalProcessingResult(
        status, executionId, executionState, stepState, result, error, List.of());
  }
}
