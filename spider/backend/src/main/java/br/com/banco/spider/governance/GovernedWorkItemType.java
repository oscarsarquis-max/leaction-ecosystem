package br.com.banco.spider.governance;

public enum GovernedWorkItemType {
  WAIT,
  INBOX_SIGNAL,
  CALLBACK_OUTBOX,
  CALLBACK_RECONCILIATION,
  EXECUTION_RECOVERY,
  STEP_ATTEMPT
}
