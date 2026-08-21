package br.com.banco.spider.execution.engine;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterResult;

/** Mapping Adapter → ExecutionState / TechnicalStatus (SPIDER-PROMPT-002). */
public final class AdapterResultMapper {

  public record MappedTerminal(ExecutionState state, TechnicalStatus technicalStatus) {}

  private AdapterResultMapper() {}

  public static MappedTerminal map(UniversalAdapterResult adapterResult) {
    AdapterDispositionMode disposition = adapterResult.dispositionMode();
    return switch (disposition) {
      case COMPLETED -> new MappedTerminal(ExecutionState.SUCCEEDED, TechnicalStatus.SUCCESS);
      case ACCEPTED_ASYNC -> new MappedTerminal(ExecutionState.WAITING_EXTERNAL, TechnicalStatus.PENDING);
      case UNKNOWN -> new MappedTerminal(ExecutionState.WAITING_EXTERNAL, TechnicalStatus.PENDING);
      case REJECTED -> mapRejected(adapterResult);
    };
  }

  private static MappedTerminal mapRejected(UniversalAdapterResult adapterResult) {
    boolean timeout =
        adapterResult.errors().stream().anyMatch(e -> e.category() == ErrorCategory.TIMEOUT);
    if (timeout) {
      return new MappedTerminal(ExecutionState.TIMED_OUT, TechnicalStatus.FAILURE);
    }
    if (adapterResult.outcome() != null
        && adapterResult.outcome().technicalStatus() == TechnicalStatus.FAILURE) {
      return new MappedTerminal(ExecutionState.FAILED, TechnicalStatus.FAILURE);
    }
    return new MappedTerminal(ExecutionState.FAILED, TechnicalStatus.FAILURE);
  }
}
