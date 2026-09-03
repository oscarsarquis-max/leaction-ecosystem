package br.com.banco.spider.context.capability;

/** Quem executaria a capability e como; nunca faz parte do Intent Contract ou do plano. */
public record CapabilityRoute(
    String routeRef,
    String adapterRef,
    String targetOperation,
    String mockScenario,
    boolean executable) {}
