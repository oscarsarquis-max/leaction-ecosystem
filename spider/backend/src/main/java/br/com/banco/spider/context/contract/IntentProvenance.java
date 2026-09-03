package br.com.banco.spider.context.contract;

/** Proveniência obrigatória e auditável da intenção. */
public record IntentProvenance(IntentProvenanceSource source, String sourceRef) {}
