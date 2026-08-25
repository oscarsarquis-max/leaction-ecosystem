package br.com.banco.spider.operational.capacity;

/** Conjunto fechado de desfechos de admissão. */
public enum AdmissionResult {
  ADMITTED,
  DELAYED,
  REJECTED_QUOTA,
  REJECTED_CAPACITY,
  REJECTED_CIRCUIT_OPEN,
  SHED;

  public boolean admitted() {
    return this == ADMITTED;
  }
}
