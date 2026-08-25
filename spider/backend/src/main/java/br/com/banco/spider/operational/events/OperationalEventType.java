package br.com.banco.spider.operational.events;

public enum OperationalEventType {
  EXECUTION_STARTED(OperationalEventCategory.EXECUTION),
  EXECUTION_SUCCEEDED(OperationalEventCategory.EXECUTION),
  EXECUTION_FAILED(OperationalEventCategory.EXECUTION),
  EXECUTION_WAITING(OperationalEventCategory.EXECUTION),
  EXECUTION_RESUMED(OperationalEventCategory.EXECUTION),
  EXECUTION_REJECTED(OperationalEventCategory.EXECUTION),
  INTERACTION_STARTED(OperationalEventCategory.INTERACTION),
  INTERACTION_COMPLETED(OperationalEventCategory.INTERACTION),
  OUTBOUND_REQUEST_STARTED(OperationalEventCategory.TRANSPORT),
  OUTBOUND_RESPONSE_RECEIVED(OperationalEventCategory.TRANSPORT),
  OUTBOUND_TIMEOUT(OperationalEventCategory.TRANSPORT),
  OUTBOUND_TRANSPORT_ERROR(OperationalEventCategory.TRANSPORT),
  CALLBACK_RECEIVED(OperationalEventCategory.CALLBACK),
  CALLBACK_ACCEPTED(OperationalEventCategory.CALLBACK),
  CALLBACK_REJECTED(OperationalEventCategory.CALLBACK),
  SIGNAL_RECEIVED(OperationalEventCategory.SIGNAL),
  SIGNAL_ACCEPTED(OperationalEventCategory.SIGNAL),
  SIGNAL_REJECTED(OperationalEventCategory.SIGNAL),
  SECURITY_INTEGRITY_REJECTED(OperationalEventCategory.SECURITY),
  SECURITY_REPLAY_REJECTED(OperationalEventCategory.SECURITY),
  SECURITY_TOKEN_REJECTED(OperationalEventCategory.SECURITY),
  SECURITY_ENVELOPE_REJECTED(OperationalEventCategory.SECURITY),
  WORKER_STARTED(OperationalEventCategory.SYSTEM),
  WORKER_DRAIN_REQUESTED(OperationalEventCategory.SYSTEM),
  WORKER_DRAINED(OperationalEventCategory.SYSTEM),
  WORKER_STOPPED(OperationalEventCategory.SYSTEM),
  SCHEDULE_CLAIMED(OperationalEventCategory.SYSTEM),
  SCHEDULE_COMPLETED(OperationalEventCategory.SYSTEM),
  SCHEDULE_FAILED(OperationalEventCategory.SYSTEM),
  WORK_ITEM_FENCED_OUT(OperationalEventCategory.SYSTEM),
  LEASE_EXPIRED(OperationalEventCategory.SYSTEM),
  BACKLOG_OBSERVED(OperationalEventCategory.SYSTEM);

  private final OperationalEventCategory category;

  OperationalEventType(OperationalEventCategory category) {
    this.category = category;
  }

  public OperationalEventCategory category() {
    return category;
  }
}
