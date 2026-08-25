package br.com.banco.spider.operational.workers;

public enum WorkerBacklogStatus {
  EMPTY,
  NORMAL,
  ACCUMULATING,
  STALE,
  UNKNOWN
}
