package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteStatus;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.List;
import reactor.core.publisher.Mono;

/** Catálogo backed por snapshot — lookup por ref exata no snapshot fixado. */
public class SnapshotBackedRouteCatalog implements RouteCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedRouteCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Mono<List<RouteDefinition>> findPublishedCandidates(
      String journeyRef, String capabilityCode, String operationCode) {
    List<RouteDefinition> list =
        snapshot.routeDefinitions().values().stream()
            .filter(r -> r.status() == RouteStatus.PUBLISHED)
            .filter(r -> journeyRef == null || journeyRef.equals(r.journeyRef()))
            .filter(
                r ->
                    capabilityCode == null
                        || capabilityCode.equals(r.target().capabilityCode()))
            .filter(
                r ->
                    operationCode == null || operationCode.equals(r.target().operationCode()))
            .toList();
    return Mono.just(list);
  }
}
