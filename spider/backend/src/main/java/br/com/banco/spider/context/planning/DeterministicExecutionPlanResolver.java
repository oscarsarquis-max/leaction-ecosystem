package br.com.banco.spider.context.planning;

import br.com.banco.spider.context.capability.BusinessCapabilityCatalog;
import br.com.banco.spider.context.capability.CapabilityAvailability;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;

/** Compõe o mesmo contrato validado no mesmo plano, sem IA, clock ou aleatoriedade. */
public final class DeterministicExecutionPlanResolver implements ExecutionPlanResolver {

  private final ExecutionPlanCatalog planCatalog;
  private final BusinessCapabilityCatalog capabilityCatalog;

  public DeterministicExecutionPlanResolver(
      ExecutionPlanCatalog planCatalog, BusinessCapabilityCatalog capabilityCatalog) {
    this.planCatalog = planCatalog;
    this.capabilityCatalog = capabilityCatalog;
  }

  @Override
  public Optional<ContextExecutionPlan> resolve(
      IntentContract contract, ContextPolicyGuard.GuardResult guard) {
    if (contract == null || guard == null || !guard.accepted()) {
      return Optional.empty();
    }
    return planCatalog
        .findByIntent(contract.intent())
        .map(template -> materialize(contract, template));
  }

  private ContextExecutionPlan materialize(
      IntentContract contract, ExecutionPlanTemplate template) {
    List<String> unavailable = new ArrayList<>();
    int availableRequired = 0;
    int required = 0;
    for (ContextExecutionPlanStep step : template.steps()) {
      if (!step.required()) {
        continue;
      }
      required++;
      boolean available =
          capabilityCatalog
              .findById(step.capabilityId())
              .map(
                  capability ->
                      capability.availability() == CapabilityAvailability.AVAILABLE
                          && !capability.eligibleRoutes().isEmpty())
              .orElse(false);
      if (available) {
        availableRequired++;
      } else {
        unavailable.add("CAPABILITY_NOT_AVAILABLE:" + step.capabilityId());
      }
    }

    ContextExecutionPlanStatus status;
    if (required == availableRequired) {
      status = ContextExecutionPlanStatus.READY;
    } else if (availableRequired > 0) {
      status = ContextExecutionPlanStatus.PARTIALLY_AVAILABLE;
    } else {
      status = ContextExecutionPlanStatus.NOT_EXECUTABLE;
    }

    return new ContextExecutionPlan(
        "1.0",
        deterministicPlanId(contract, template),
        template.planType(),
        contract.intent(),
        template.steps(),
        contract.constraints(),
        contract.provenance(),
        status,
        unavailable);
  }

  private static String deterministicPlanId(
      IntentContract contract, ExecutionPlanTemplate template) {
    StringBuilder canonical =
        new StringBuilder()
            .append(contract.schemaVersion())
            .append('|')
            .append(contract.intent())
            .append('|')
            .append(template.planType());
    contract.entities().entrySet().stream()
        .sorted(java.util.Map.Entry.comparingByKey())
        .forEach(
            entry ->
                canonical
                    .append('|')
                    .append(entry.getKey())
                    .append('=')
                    .append(entry.getValue()));
    try {
      byte[] digest =
          MessageDigest.getInstance("SHA-256")
              .digest(canonical.toString().getBytes(StandardCharsets.UTF_8));
      return "ctxp-" + HexFormat.of().formatHex(digest, 0, 12);
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 unavailable", exception);
    }
  }
}
