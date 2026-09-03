package br.com.banco.spider.context.domain;

import br.com.banco.spider.context.contract.IntentContract;
import java.util.Optional;

public final class DeterministicIntentRouter {

  private final BusinessIntentCatalog catalog;

  public DeterministicIntentRouter(BusinessIntentCatalog catalog) {
    this.catalog = catalog;
  }

  public Optional<IntentRouteResolution> resolve(
      IntentContract contract, ContextPolicyGuard.GuardResult guard) {
    if (contract == null || guard == null || !guard.accepted()) {
      return Optional.empty();
    }
    return catalog
        .findByIntent(contract.intent())
        .map(
            definition ->
                new IntentRouteResolution(
                    definition.intent(),
                    definition.capabilityRef(),
                    definition.routeRef(),
                    definition.executable(),
                    definition.targetOperation(),
                    definition.mockScenario(),
                    guard.policyRef()));
  }
}
