package br.com.banco.spider.execution.route;

import java.util.List;
import reactor.core.publisher.Mono;

public interface RouteCatalogPort {
  Mono<List<RouteDefinition>> findPublishedCandidates(
      String journeyRef, String capabilityCode, String operationCode);
}
