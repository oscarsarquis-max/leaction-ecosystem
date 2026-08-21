package br.com.banco.spider.execution.plan;

import java.util.Objects;

public record RouteRef(String routeCode, String routeVersion) {
  public RouteRef {
    Objects.requireNonNull(routeCode, "routeCode");
    Objects.requireNonNull(routeVersion, "routeVersion");
    if (routeCode.isBlank() || routeVersion.isBlank()) {
      throw new IllegalArgumentException("routeCode/routeVersion must not be blank");
    }
  }
}
