package br.com.banco.spider.execution.step;

/** Estados técnicos do step (SPIDER-ARCH-005). */
public enum StepState {
  PENDING,
  READY,
  RUNNING,
  WAITING_EXTERNAL,
  SUCCEEDED,
  FAILED,
  SKIPPED,
  TIMED_OUT,
  CANCELLED,
  COMPENSATING,
  COMPENSATED,
  COMPENSATION_FAILED;

  public boolean isTerminal() {
    return this == SUCCEEDED
        || this == FAILED
        || this == SKIPPED
        || this == TIMED_OUT
        || this == CANCELLED
        || this == COMPENSATED
        || this == COMPENSATION_FAILED;
  }
}
