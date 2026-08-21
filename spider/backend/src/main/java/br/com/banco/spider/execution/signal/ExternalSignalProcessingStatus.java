package br.com.banco.spider.execution.signal;

public enum ExternalSignalProcessingStatus {
  ACCEPTED_AND_RESUMED,
  ACCEPTED_AND_TERMINATED,
  DUPLICATE,
  CONFLICT,
  REJECTED,
  LATE_REJECTED,
  ORPHANED
}
