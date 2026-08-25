package br.com.banco.spider.operational.workers;

public enum WorkerRuntimeStatus {
  DISABLED,
  HEALTHY,
  DEGRADED,
  DRAINING,
  STOPPED,
  UNKNOWN
}
