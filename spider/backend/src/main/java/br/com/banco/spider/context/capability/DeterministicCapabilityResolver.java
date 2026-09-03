package br.com.banco.spider.context.capability;

import br.com.banco.spider.context.planning.ContextExecutionPlan;
import java.util.Comparator;
import java.util.List;

/** Resolve capabilities por catálogo controlado, sem participação de IA. */
public final class DeterministicCapabilityResolver implements CapabilityResolver {

  private final BusinessCapabilityCatalog catalog;

  public DeterministicCapabilityResolver(BusinessCapabilityCatalog catalog) {
    this.catalog = catalog;
  }

  @Override
  public List<CapabilityResolution> resolve(ContextExecutionPlan plan) {
    if (plan == null) {
      return List.of();
    }
    return plan.steps().stream()
        .map(
            step ->
                catalog
                    .findById(step.capabilityId())
                    .map(
                        capability -> {
                          CapabilityRoute route =
                              capability.eligibleRoutes().stream()
                                  .sorted(Comparator.comparing(CapabilityRoute::routeRef))
                                  .findFirst()
                                  .orElse(null);
                          boolean resolved =
                              capability.availability() == CapabilityAvailability.AVAILABLE
                                  && route != null;
                          return new CapabilityResolution(
                              step.stepId(),
                              capability.capabilityId(),
                              capability.description(),
                              step.reason(),
                              capability.inputContract(),
                              capability.outputContract(),
                              capability.mutationType(),
                              capability.availability(),
                              resolved
                                  ? CapabilityResolutionStatus.RESOLVED
                                  : CapabilityResolutionStatus.UNAVAILABLE,
                              route);
                        })
                    .orElseGet(
                        () ->
                            new CapabilityResolution(
                                step.stepId(),
                                step.capabilityId(),
                                "Capability ausente do catálogo canônico.",
                                step.reason(),
                                null,
                                null,
                                CapabilityMutationType.READ_ONLY,
                                CapabilityAvailability.NOT_AVAILABLE,
                                CapabilityResolutionStatus.UNAVAILABLE,
                                null)))
        .toList();
  }
}
