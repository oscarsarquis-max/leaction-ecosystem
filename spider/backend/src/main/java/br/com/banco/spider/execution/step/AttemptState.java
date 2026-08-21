package br.com.banco.spider.execution.step;

/** Estado de uma attempt individual. */
public enum AttemptState {
  STARTED,
  SUCCEEDED,
  FAILED,
  TIMED_OUT,
  WAITING_EXTERNAL,
  UNKNOWN
}
