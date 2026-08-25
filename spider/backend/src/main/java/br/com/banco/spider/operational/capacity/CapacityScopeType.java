package br.com.banco.spider.operational.capacity;

/**
 * Escopos fechados de governo de capacidade, do mais genérico ao mais específico. A ordem declarada
 * define a especificidade usada na resolução da política efetiva.
 */
public enum CapacityScopeType {
  GLOBAL(1),
  SERVICE_CLASS(2),
  WORKER_TYPE(3),
  SCHEDULE(4),
  ADAPTER_BINDING(5);

  /** Referência reservada do escopo global — nunca confundível com um código real. */
  public static final String GLOBAL_SCOPE_REF = "GLOBAL";

  private final int specificity;

  CapacityScopeType(int specificity) {
    this.specificity = specificity;
  }

  public int specificity() {
    return specificity;
  }
}
