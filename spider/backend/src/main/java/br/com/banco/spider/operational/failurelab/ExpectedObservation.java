package br.com.banco.spider.operational.failurelab;

import java.util.Objects;

/**
 * Observação declarada por um cenário. {@code expectedValue} é sempre texto seguro (nome de enum,
 * número ou literal booleano) — nunca conteúdo de negócio.
 */
public record ExpectedObservation(
    String code,
    String description,
    String sourceType,
    ObservationPredicateType predicateType,
    String expectedValue,
    boolean required) {

  public ExpectedObservation {
    code = require("code", code);
    description = description == null ? "" : description.trim();
    sourceType = require("sourceType", sourceType);
    Objects.requireNonNull(predicateType, "predicateType");
    expectedValue = expectedValue == null ? "" : expectedValue.trim();
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String trimmed = value.trim();
    if (trimmed.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return trimmed;
  }
}
