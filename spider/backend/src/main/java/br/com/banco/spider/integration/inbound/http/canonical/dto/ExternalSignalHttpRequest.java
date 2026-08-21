package br.com.banco.spider.integration.inbound.http.canonical.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/** DTO de transporte HTTP — sem Security Context fornecido pelo cliente. */
public record ExternalSignalHttpRequest(
    String signalContractVersion,
    String messageId,
    String sourceRef,
    String bindingRef,
    String contractRef,
    String executionId,
    String stepId,
    String externalOperationRef,
    Instant occurredAt,
    String correlationId,
    CompletionDto completion,
    String continuationToken) {

  /** Compat legado sem token. */
  public ExternalSignalHttpRequest(
      String signalContractVersion,
      String messageId,
      String sourceRef,
      String bindingRef,
      String contractRef,
      String executionId,
      String stepId,
      String externalOperationRef,
      Instant occurredAt,
      String correlationId,
      CompletionDto completion) {
    this(
        signalContractVersion,
        messageId,
        sourceRef,
        bindingRef,
        contractRef,
        executionId,
        stepId,
        externalOperationRef,
        occurredAt,
        correlationId,
        completion,
        null);
  }

  public record CompletionDto(
      String disposition, Map<String, Object> outcome, List<Map<String, Object>> errors) {}
}
