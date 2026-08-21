package br.com.banco.spider.execution.wait;

public enum WaitState {
  WAITING,
  SIGNALLED,
  EXPIRING,
  EXPIRED,
  RESUMING,
  RESUMED,
  RECONCILIATION_REQUIRED,
  CANCELLED;

  public boolean isTerminal() {
    return this == EXPIRED
        || this == RESUMED
        || this == RECONCILIATION_REQUIRED
        || this == CANCELLED;
  }

  public boolean isActive() {
    return this == WAITING || this == SIGNALLED || this == EXPIRING || this == RESUMING;
  }
}
