package br.com.banco.spider.execution.route;

/** Ciclo de vida governado da rota. Somente PUBLISHED é elegível. */
public enum RouteStatus {
  DRAFT,
  VALIDATED,
  APPROVED,
  PUBLISHED,
  DEPRECATED,
  RETIRED;

  public boolean isEligible() {
    return this == PUBLISHED;
  }
}
