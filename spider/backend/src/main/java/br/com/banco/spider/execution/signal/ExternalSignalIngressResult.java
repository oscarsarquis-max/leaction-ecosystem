package br.com.banco.spider.execution.signal;

import java.util.Objects;

public record ExternalSignalIngressResult(
    ExternalSignalIngressOutcome outcome,
    String safeReasonCategory,
    ExternalSignalProcessingResult legacyResult) {

  public ExternalSignalIngressResult {
    Objects.requireNonNull(outcome, "outcome");
  }

  public static ExternalSignalIngressResult of(
      ExternalSignalIngressOutcome outcome, String safeReasonCategory) {
    return new ExternalSignalIngressResult(outcome, safeReasonCategory, null);
  }

  public static ExternalSignalIngressResult legacy(ExternalSignalProcessingResult result) {
    ExternalSignalIngressOutcome mapped =
        switch (result.processingStatus()) {
          case ACCEPTED_AND_RESUMED, ACCEPTED_AND_TERMINATED ->
              ExternalSignalIngressOutcome.APPLIED_INLINE;
          case DUPLICATE -> ExternalSignalIngressOutcome.DUPLICATE_ALREADY_APPLIED;
          case CONFLICT -> ExternalSignalIngressOutcome.REPLAY_CONFLICT;
          case REJECTED -> ExternalSignalIngressOutcome.REJECTED;
          case LATE_REJECTED -> ExternalSignalIngressOutcome.LATE;
          case ORPHANED -> ExternalSignalIngressOutcome.ORPHAN;
        };
    return new ExternalSignalIngressResult(mapped, result.processingStatus().name(), result);
  }
}
