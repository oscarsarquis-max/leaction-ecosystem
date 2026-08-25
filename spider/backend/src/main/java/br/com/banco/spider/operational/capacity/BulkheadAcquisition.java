package br.com.banco.spider.operational.capacity;

/**
 * Resultado de uma tentativa de reserva no bulkhead. {@code NOT_REQUIRED} distingue "não há limite
 * declarado para o escopo" de "o limite está esgotado" — sem isso o chamador descartaria trabalho
 * legítimo em escopos sem política de concorrência.
 */
public enum BulkheadAcquisition {
  ACQUIRED,
  NOT_REQUIRED,
  SATURATED;

  public boolean held() {
    return this == ACQUIRED;
  }
}
