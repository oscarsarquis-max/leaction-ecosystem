package br.com.banco.spider.execution.signal.protection;

public enum ProtectedEnvelopeState {
  AVAILABLE,
  CLAIMED,
  CONSUMED,
  CORRUPT,
  KEY_UNAVAILABLE,
  QUARANTINED,
  DELETION_ELIGIBLE,
  DELETED_TOMBSTONE
}
