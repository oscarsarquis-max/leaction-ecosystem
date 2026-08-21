package br.com.banco.spider.execution.inbox;

public record InboxReservationResult(
    InboxReservationStatus status, InboxRecord record, String reasonCode) {

  public static InboxReservationResult reserved(InboxRecord record) {
    return new InboxReservationResult(InboxReservationStatus.RESERVED_NEW, record, null);
  }

  public static InboxReservationResult duplicate(InboxRecord record) {
    return new InboxReservationResult(
        InboxReservationStatus.DUPLICATE_SAME_SIGNAL, record, "DUPLICATE");
  }

  public static InboxReservationResult conflict(InboxRecord record) {
    return new InboxReservationResult(
        InboxReservationStatus.CONFLICTING_SIGNAL, record, "CONFLICT");
  }

  public static InboxReservationResult inProgress(InboxRecord record) {
    return new InboxReservationResult(
        InboxReservationStatus.EXISTING_IN_PROGRESS, record, "IN_PROGRESS");
  }
}
