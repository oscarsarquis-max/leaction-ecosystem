package br.com.segsense.domain.demo;

import java.time.Instant;
import java.util.UUID;

public record DemoProtectionJourney(
    UUID id,
    String scenarioKey,
    String declaredObjective,
    String status,
    String correlationId,
    String idempotencyKeyHash,
    String spiderDecisionId,
    String mockResultId,
    String failureKind,
    String projectionJson,
    Instant createdAt,
    Instant updatedAt) {}
