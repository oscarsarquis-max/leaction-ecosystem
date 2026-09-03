package br.com.banco.spider.context.capability;

import java.util.List;

/** Competência empresarial independente de sistema, endpoint e protocolo. */
public record BusinessCapability(
    String capabilityId,
    String version,
    String description,
    String inputContract,
    String outputContract,
    CapabilityMutationType mutationType,
    CapabilityAvailability availability,
    List<CapabilityRoute> eligibleRoutes) {

  public BusinessCapability {
    eligibleRoutes = eligibleRoutes == null ? List.of() : List.copyOf(eligibleRoutes);
  }
}
