package br.com.banco.spider.context.domain;

/** Resultado determinístico: intent, capability e route permanecem conceitos distintos. */
public record IntentRouteResolution(
    String intent,
    String capabilityRef,
    String routeRef,
    boolean executable,
    String targetOperation,
    String mockScenario,
    String policyRef) {}
