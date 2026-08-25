package br.com.banco.spider.operational.failurelab;

/** Ciclo de vida de uma execução controlada do Failure Lab (SPIDER-PROMPT-018). */
public enum FailureLabRunStatus {
  REQUESTED,
  RUNNING,
  OBSERVING,
  VERIFIED,
  FAILED,
  TIMED_OUT,
  CANCELLED,
  INCONCLUSIVE;

  public boolean isActive() {
    return this == REQUESTED || this == RUNNING || this == OBSERVING;
  }

  public boolean isTerminal() {
    return !isActive();
  }
}
