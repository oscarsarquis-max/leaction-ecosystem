package br.com.banco.spider.operational.capacity;

/** Chave textual estável de um escopo — usada como identidade de bulkhead, disjuntor e quota. */
public final class CapacityScopeKey {

  private CapacityScopeKey() {}

  public static String of(CapacityScopeType scopeType, String scopeRef) {
    if (scopeType == null) {
      return CapacityScopeType.GLOBAL.name() + ":" + CapacityScopeType.GLOBAL_SCOPE_REF;
    }
    String ref =
        scopeRef == null || scopeRef.isBlank()
            ? CapacityScopeType.GLOBAL_SCOPE_REF
            : scopeRef.trim();
    return scopeType.name() + ":" + ref;
  }
}
