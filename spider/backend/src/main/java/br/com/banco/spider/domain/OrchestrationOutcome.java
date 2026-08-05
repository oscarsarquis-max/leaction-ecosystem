package br.com.banco.spider.domain;

import java.util.Map;

public record OrchestrationOutcome(
    String traceparent,
    String productId,
    String transactionId,
    String technicalStatus,
    int legacyHttpStatus,
    long latencyMs,
    String stateTransitionToken,
    Map<String, Object> legacyBody) {}
