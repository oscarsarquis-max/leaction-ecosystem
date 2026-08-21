package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.security.integrity.IntegrityProof;
import java.time.Instant;
import java.util.Objects;

public record ExternalSignalEnvelope(
    String signalContractVersion,
    String messageId,
    String sourceRef,
    String bindingRef,
    String contractRef,
    String executionId,
    String stepId,
    String externalOperationRef,
    Instant occurredAt,
    Instant receivedAt,
    String correlationId,
    TraceDescriptor trace,
    SignalSecurityContext securityContext,
    SignalCompletion completion,
    IntegrityProof integrityProof,
    String continuationToken) {

  public ExternalSignalEnvelope {
    Objects.requireNonNull(signalContractVersion, "signalContractVersion");
    Objects.requireNonNull(messageId, "messageId");
    Objects.requireNonNull(sourceRef, "sourceRef");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(contractRef, "contractRef");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(receivedAt, "receivedAt");
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(securityContext, "securityContext");
    Objects.requireNonNull(completion, "completion");
  }

  public ExternalSignalEnvelope(
      String signalContractVersion,
      String messageId,
      String sourceRef,
      String bindingRef,
      String contractRef,
      String executionId,
      String stepId,
      String externalOperationRef,
      Instant occurredAt,
      Instant receivedAt,
      String correlationId,
      TraceDescriptor trace,
      SignalSecurityContext securityContext,
      SignalCompletion completion,
      IntegrityProof integrityProof) {
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
        receivedAt,
        correlationId,
        trace,
        securityContext,
        completion,
        integrityProof,
        null);
  }

  public ExternalSignalEnvelope(
      String signalContractVersion,
      String messageId,
      String sourceRef,
      String bindingRef,
      String contractRef,
      String executionId,
      String stepId,
      String externalOperationRef,
      Instant occurredAt,
      Instant receivedAt,
      String correlationId,
      TraceDescriptor trace,
      SignalSecurityContext securityContext,
      SignalCompletion completion) {
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
        receivedAt,
        correlationId,
        trace,
        securityContext,
        completion,
        null,
        null);
  }
}
