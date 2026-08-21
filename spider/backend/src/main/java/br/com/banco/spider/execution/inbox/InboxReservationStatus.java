package br.com.banco.spider.execution.inbox;

public enum InboxReservationStatus {
  RESERVED_NEW,
  DUPLICATE_SAME_SIGNAL,
  CONFLICTING_SIGNAL,
  EXISTING_IN_PROGRESS
}
