package br.com.banco.spider.domain;

import java.util.List;

/** Contrato de definição de rota/produto (espelha definition_json). */
public record ProductRouteDefinition(List<StepDefinition> steps) {

  public record StepDefinition(String name, String system, String mode) {}
}
