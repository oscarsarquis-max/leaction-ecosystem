package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.ExecutionPolicyReference;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.SignalCompletion;
import br.com.banco.spider.execution.signal.SignalSecurityContext;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.integration.inbound.http.canonical.dto.CanonicalExecutionHttpRequest;
import br.com.banco.spider.integration.inbound.http.canonical.dto.ExternalSignalHttpRequest;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class CanonicalExecutionHttpMapper {

  private final ObjectMapper mapper;

  public CanonicalExecutionHttpMapper(ObjectMapper mapper) {
    this.mapper = mapper;
  }

  public CanonicalExecutionRequest toCanonical(CanonicalExecutionHttpRequest http) {
    String executionId = http.execution() == null ? null : http.execution().executionId();
    if (executionId == null || executionId.isBlank()) {
      executionId = IdentifierGenerator.uuid().nextId("exec");
    }
    Instant requestedAt =
        http.execution() != null && http.execution().requestedAt() != null
            ? http.execution().requestedAt()
            : Instant.now();
    String idempotencyKey = http.execution() == null ? null : http.execution().idempotencyKey();
    return CanonicalExecutionRequest.builder()
        .contract(
            new ContractDescriptor(
                http.contract().schemaVersion(), http.contract().contractVersion()))
        .execution(new ExecutionIdentity(executionId, requestedAt, idempotencyKey))
        .contextRef(
            new ContextReference(
                http.contextRef().contextId(),
                http.contextRef().intentId(),
                http.contextRef().capabilityId(),
                http.contextRef().productServiceId() != null
                    ? http.contextRef().productServiceId()
                    : http.contextRef().capabilityId(),
                http.contextRef().journeyId()))
        .origin(
            new OriginDescriptor(
                http.origin().channel(),
                http.origin().originatorId(),
                http.origin().interactionRef()))
        .trace(
            new TraceDescriptor(
                http.trace().correlationId(),
                http.trace().traceparent(),
                http.trace().tracestate()))
        .target(new TargetDescriptor(http.target().capability(), http.target().operation()))
        .payload(
            http.payload() == null || http.payload().canonicalData() == null
                ? CanonicalPayload.empty()
                : CanonicalPayload.of(http.payload().canonicalData()))
        .executionPolicy(ExecutionPolicyReference.empty())
        .callbackRef(
            http.callbackRef() == null || http.callbackRef().isBlank()
                ? null
                : VersionedReference.of(http.callbackRef(), "1.0.0"))
        .build();
  }

  public ExternalSignalEnvelope toEnvelope(
      ExternalSignalHttpRequest http, SignalSecurityContext security, Instant receivedAt) {
    AdapterDispositionMode disposition =
        AdapterDispositionMode.valueOf(http.completion().disposition());
    CanonicalOutcome outcome =
        CanonicalOutcome.technical(TechnicalStatus.SUCCESS);
    if (http.completion().outcome() != null
        && http.completion().outcome().get("technicalStatus") != null) {
      outcome =
          CanonicalOutcome.technical(
              TechnicalStatus.valueOf(
                  String.valueOf(http.completion().outcome().get("technicalStatus"))));
    }
    return new ExternalSignalEnvelope(
        http.signalContractVersion(),
        http.messageId(),
        http.sourceRef(),
        http.bindingRef(),
        http.contractRef(),
        http.executionId(),
        http.stepId(),
        http.externalOperationRef(),
        http.occurredAt(),
        receivedAt,
        http.correlationId(),
        new TraceDescriptor(
            http.correlationId(),
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            null),
        security,
        new SignalCompletion(disposition, outcome, List.of(), List.of()),
        null,
        http.continuationToken());
  }
}
