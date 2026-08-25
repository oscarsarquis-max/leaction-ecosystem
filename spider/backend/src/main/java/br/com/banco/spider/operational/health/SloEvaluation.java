package br.com.banco.spider.operational.health;

public record SloEvaluation(
    int schemaVersion,
    String objectiveCode,
    String sliCode,
    SloComplianceStatus status,
    Double observedValue,
    Double targetValue,
    String explanation) {}
