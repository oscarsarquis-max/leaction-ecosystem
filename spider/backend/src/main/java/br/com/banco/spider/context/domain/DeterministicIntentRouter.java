package br.com.banco.spider.context.domain;

import br.com.banco.spider.context.capability.CapabilityResolution;
import br.com.banco.spider.context.capability.CapabilityResolutionStatus;
import br.com.banco.spider.context.planning.ContextExecutionPlan;
import br.com.banco.spider.context.planning.ContextExecutionPlanStatus;
import java.util.List;
import java.util.Optional;

/**
 * Fachada de compatibilidade para a rota primária do fluxo atual.
 *
 * <p>Não recebe Intent Contract: a rota só pode surgir depois de Plan e Capability Resolution.
 */
public final class DeterministicIntentRouter {

  public Optional<IntentRouteResolution> resolvePrimaryRoute(
      ContextExecutionPlan plan,
      List<CapabilityResolution> capabilities,
      ContextPolicyGuard.GuardResult guard) {
    if (plan == null
        || capabilities == null
        || guard == null
        || !guard.accepted()
        || capabilities.size() != 1) {
      return Optional.empty();
    }
    CapabilityResolution resolution = capabilities.getFirst();
    if (resolution.selectedRoute() == null) {
      return Optional.empty();
    }
    var selected = resolution.selectedRoute();
    boolean executable =
        plan.status() == ContextExecutionPlanStatus.READY
            && resolution.status() == CapabilityResolutionStatus.RESOLVED
            && selected.executable();
    return Optional.of(
        new IntentRouteResolution(
            plan.intent(),
            resolution.capabilityId(),
            selected.routeRef(),
            executable,
            selected.targetOperation(),
            selected.mockScenario(),
            guard.policyRef()));
  }
}
