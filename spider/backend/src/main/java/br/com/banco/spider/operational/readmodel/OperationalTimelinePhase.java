package br.com.banco.spider.operational.readmodel;

public enum OperationalTimelinePhase {
  INGRESS,
  VALIDATION,
  GOVERNANCE,
  PLANNING,
  STEP_EXECUTION,
  WAITING_EXTERNAL,
  SIGNAL,
  RESULT,
  CALLBACK,
  RECONCILIATION,
  SECURITY,
  RECOVERY
}
