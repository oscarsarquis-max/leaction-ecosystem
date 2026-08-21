package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.util.List;
import java.util.Objects;

/** Resultado interno da resolução de rota. */
public record RouteResolution(
    boolean selected,
    RouteDefinition selectedRoute,
    RouteResolutionReasonCode reasonCode,
    List<String> candidateRouteCodes,
    List<CanonicalError> errors,
    String detail) {

  public RouteResolution {
    Objects.requireNonNull(reasonCode, "reasonCode");
    candidateRouteCodes =
        candidateRouteCodes == null ? List.of() : List.copyOf(candidateRouteCodes);
    errors = errors == null ? List.of() : List.copyOf(errors);
  }

  public static RouteResolution selected(RouteDefinition route, List<String> candidates) {
    return new RouteResolution(
        true, route, RouteResolutionReasonCode.ROUTE_SELECTED, candidates, List.of(), null);
  }

  public static RouteResolution rejected(
      RouteResolutionReasonCode reason, List<String> candidates, List<CanonicalError> errors, String detail) {
    return new RouteResolution(false, null, reason, candidates, errors, detail);
  }
}
