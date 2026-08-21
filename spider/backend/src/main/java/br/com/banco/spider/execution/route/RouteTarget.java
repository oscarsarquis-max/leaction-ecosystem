package br.com.banco.spider.execution.route;

import java.util.Objects;

/** Target canônico da rota — sem detalhe físico. */
public record RouteTarget(String capabilityCode, String operationCode) {

  public RouteTarget {
    capabilityCode = require("capabilityCode", capabilityCode);
    operationCode = require("operationCode", operationCode);
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String t = value.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return t;
  }
}
