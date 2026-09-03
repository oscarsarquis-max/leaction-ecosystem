package br.com.banco.spider.context.capability;

/** Resolução determinística e explicável de uma capability do plano. */
public record CapabilityResolution(
    String stepId,
    String capabilityId,
    String description,
    String reason,
    String inputContract,
    String outputContract,
    CapabilityMutationType mutationType,
    CapabilityAvailability availability,
    CapabilityResolutionStatus status,
    CapabilityRoute selectedRoute) {}
