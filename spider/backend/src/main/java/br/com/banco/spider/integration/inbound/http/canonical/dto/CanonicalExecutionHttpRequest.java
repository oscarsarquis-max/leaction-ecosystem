package br.com.banco.spider.integration.inbound.http.canonical.dto;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;

/** Envelope JSON do perfil HTTP de submissão (subset controlado). */
public record CanonicalExecutionHttpRequest(
    ContractDto contract,
    ExecutionDto execution,
    ContextDto contextRef,
    OriginDto origin,
    TraceDto trace,
    TargetDto target,
    PayloadDto payload,
    String callbackRef) {

  public record ContractDto(String schemaVersion, String contractVersion) {}

  public record ExecutionDto(String executionId, Instant requestedAt, String idempotencyKey) {}

  public record ContextDto(
      String contextId,
      String intentId,
      String capabilityId,
      String productServiceId,
      String journeyId) {}

  public record OriginDto(String channel, String originatorId, String interactionRef) {}

  public record TraceDto(String correlationId, String traceparent, String tracestate) {}

  public record TargetDto(String capability, String operation) {}

  public record PayloadDto(JsonNode canonicalData) {}
}
