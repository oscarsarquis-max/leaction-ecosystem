package br.com.banco.spider.operational.workers;

public enum WorkerInstanceStatus {
  STARTING,
  IDLE,
  RUNNING,
  DRAINING,
  STOPPED,
  FAILED,
  STALE;

  public boolean active() {
    return this == STARTING || this == IDLE || this == RUNNING;
  }
}
