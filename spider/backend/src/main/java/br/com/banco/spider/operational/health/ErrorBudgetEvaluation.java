package br.com.banco.spider.operational.health;

public record ErrorBudgetEvaluation(
    int schemaVersion,
    String objectiveCode,
    ErrorBudgetStatus status,
    Double allowedFailureRatio,
    Double observedFailureRatio,
    Double consumedRatio,
    String explanation) {}
