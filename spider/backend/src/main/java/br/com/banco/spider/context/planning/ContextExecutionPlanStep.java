package br.com.banco.spider.context.planning;

/** Step empresarial: referencia capability, nunca endpoint, adapter ou sistema. */
public record ContextExecutionPlanStep(
    String stepId,
    int sequence,
    String capabilityId,
    boolean required,
    String reason,
    String condition) {}
