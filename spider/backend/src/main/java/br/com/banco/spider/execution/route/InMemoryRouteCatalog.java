package br.com.banco.spider.execution.route;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import reactor.core.publisher.Mono;

/**
 * Catálogo imutável em memória para desenvolvimento/testes. Não é Control Plane.
 */
public final class InMemoryRouteCatalog implements RouteCatalogPort {

  private final List<RouteDefinition> routes;

  public InMemoryRouteCatalog(List<RouteDefinition> routes) {
    Objects.requireNonNull(routes, "routes");
    this.routes = List.copyOf(routes);
  }

  @Override
  public Mono<List<RouteDefinition>> findPublishedCandidates(
      String journeyRef, String capabilityCode, String operationCode) {
    return Mono.fromCallable(
        () -> {
          List<RouteDefinition> matched = new ArrayList<>();
          for (RouteDefinition route : routes) {
            if (route.status() != RouteStatus.PUBLISHED) {
              continue;
            }
            if (!route.journeyRef().equals(journeyRef)) {
              continue;
            }
            if (!route.target().capabilityCode().equals(capabilityCode)) {
              continue;
            }
            if (!route.target().operationCode().equals(operationCode)) {
              continue;
            }
            matched.add(route);
          }
          return List.copyOf(matched);
        });
  }

  public List<RouteDefinition> all() {
    return routes;
  }
}
