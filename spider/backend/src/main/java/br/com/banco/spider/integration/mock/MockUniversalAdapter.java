package br.com.banco.spider.integration.mock;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.integration.port.ContinuationDescriptor;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * Adapter Mock atrás da Porta Universal. Selecionado por {@code spider.adapter.mock.enabled=true}.
 * Cenário via {@code payload.canonicalData.mockScenario} ou default SUCCESS.
 */
@Component
@ConditionalOnProperty(name = "spider.adapter.mock.enabled", havingValue = "true", matchIfMissing = true)
public class MockUniversalAdapter implements UniversalAdapterPort {

  public static final String ADAPTER_ID = "mock-universal-adapter";

  private final ObjectMapper objectMapper;

  public MockUniversalAdapter(ObjectMapper objectMapper) {
    this.objectMapper = objectMapper;
  }

  @Override
  public Mono<UniversalAdapterResult> invoke(UniversalAdapterRequest request) {
    Instant started = Instant.now();
    MockAdapterScenario scenario = resolveScenario(request);
    String correlation = request.trace().correlationId();

    if (scenario == MockAdapterScenario.TIMEOUT) {
      return Mono.delay(Duration.ofMillis(50))
          .then(
              Mono.fromSupplier(
                  () ->
                      base(request, started, correlation)
                          .dispositionMode(AdapterDispositionMode.REJECTED)
                          .completedAt(Instant.now())
                          .errors(
                              List.of(
                                  CanonicalError.builder()
                                      .errorId("err-" + UUID.randomUUID())
                                      .code("TIME_ADAPTER_DEADLINE")
                                      .category(ErrorCategory.TIMEOUT)
                                      .severity(ErrorSeverity.ERROR)
                                      .message("Simulated adapter timeout")
                                      .retryable(true)
                                      .occurredAt(Instant.now())
                                      .source(
                                          new CanonicalError.ErrorSource(
                                              "adapter",
                                              request.stepId(),
                                              ADAPTER_ID,
                                              request.bindingRef()))
                                      .build()))
                          .evidenceRefs(
                              List.of(
                                  new EvidenceReference(
                                      "ev-" + UUID.randomUUID(), "mock-timeout")))
                          .build()));
    }

    return Mono.fromSupplier(() -> buildImmediate(request, started, correlation, scenario));
  }

  private UniversalAdapterResult buildImmediate(
      UniversalAdapterRequest request,
      Instant started,
      String correlation,
      MockAdapterScenario scenario) {
    var builder =
        base(request, started, correlation)
            .completedAt(Instant.now())
            .evidenceRefs(
                List.of(new EvidenceReference("ev-" + UUID.randomUUID(), "mock-invocation")));

    return switch (scenario) {
      case SUCCESS ->
          builder
              .dispositionMode(AdapterDispositionMode.COMPLETED)
              .outcome(CanonicalOutcome.technical(TechnicalStatus.SUCCESS))
              .build();
      case BUSINESS_NEGATIVE -> {
        ObjectNode biz = objectMapper.createObjectNode();
        biz.put("type", "MOCK_NEGATIVE_OUTCOME");
        biz.put("schemaVersion", "1.0");
        biz.put("accepted", false);
        yield builder
            .dispositionMode(AdapterDispositionMode.COMPLETED)
            .outcome(new CanonicalOutcome(TechnicalStatus.SUCCESS, biz, null))
            .errors(
                List.of(
                    CanonicalError.builder()
                        .errorId("err-" + UUID.randomUUID())
                        .code("BIZ_MOCK_NEGATIVE")
                        .category(ErrorCategory.BUSINESS_OUTCOME)
                        .severity(ErrorSeverity.INFO)
                        .message("Delegated negative business outcome (mock)")
                        .retryable(false)
                        .occurredAt(Instant.now())
                        .source(
                            new CanonicalError.ErrorSource(
                                "adapter", request.stepId(), ADAPTER_ID, request.bindingRef()))
                        .build()))
            .build();
      }
      case TECHNICAL_FAILURE ->
          builder
              .dispositionMode(AdapterDispositionMode.REJECTED)
              .outcome(CanonicalOutcome.technical(TechnicalStatus.FAILURE))
              .errors(
                  List.of(
                      CanonicalError.builder()
                          .errorId("err-" + UUID.randomUUID())
                          .code("UNAV_MOCK_FAILURE")
                          .category(ErrorCategory.UNAVAILABLE)
                          .severity(ErrorSeverity.ERROR)
                          .message("Simulated technical failure")
                          .retryable(true)
                          .occurredAt(Instant.now())
                          .source(
                              new CanonicalError.ErrorSource(
                                  "adapter", request.stepId(), ADAPTER_ID, request.bindingRef()))
                          .build()))
              .build();
      case INVALID_RESPONSE ->
          builder
              .dispositionMode(AdapterDispositionMode.REJECTED)
              .errors(
                  List.of(
                      CanonicalError.builder()
                          .errorId("err-" + UUID.randomUUID())
                          .code("CON_INVALID_RESPONSE")
                          .category(ErrorCategory.CONTRACT)
                          .severity(ErrorSeverity.ERROR)
                          .message("Simulated invalid adapter response")
                          .retryable(false)
                          .occurredAt(Instant.now())
                          .source(
                              new CanonicalError.ErrorSource(
                                  "adapter", request.stepId(), ADAPTER_ID, request.bindingRef()))
                          .build()))
              .build();
      case UNKNOWN ->
          builder
              .dispositionMode(AdapterDispositionMode.UNKNOWN)
              .outcome(CanonicalOutcome.technical(TechnicalStatus.PENDING))
              .errors(
                  List.of(
                      CanonicalError.builder()
                          .errorId("err-" + UUID.randomUUID())
                          .code("INT_INCONCLUSIVE")
                          .category(ErrorCategory.INTERNAL)
                          .severity(ErrorSeverity.WARNING)
                          .message("Simulated inconclusive adapter state")
                          .retryable(true)
                          .occurredAt(Instant.now())
                          .source(
                              new CanonicalError.ErrorSource(
                                  "adapter", request.stepId(), ADAPTER_ID, request.bindingRef()))
                          .build()))
              .build();
      case ACCEPTED_ASYNC ->
          builder
              .dispositionMode(AdapterDispositionMode.ACCEPTED_ASYNC)
              .outcome(CanonicalOutcome.technical(TechnicalStatus.PENDING))
              .evidenceRefs(
                  List.of(new EvidenceReference("ev-" + UUID.randomUUID(), "mock-async-accept")))
              .continuation(
                  new ContinuationDescriptor(
                      "ext-op-" + request.executionId() + "-" + request.stepId(),
                      "contract:signal:async-completion@1.0",
                      Instant.now().plusSeconds(300),
                      "source:mock-async@1.0",
                      List.of()))
              .build();
      case TIMEOUT -> builder.dispositionMode(AdapterDispositionMode.REJECTED).build();
    };
  }

  private UniversalAdapterResult.Builder base(
      UniversalAdapterRequest request, Instant started, String correlation) {
    return UniversalAdapterResult.builder()
        .invocationId(request.invocationId())
        .executionId(request.executionId())
        .stepId(request.stepId())
        .attemptId(request.attemptId())
        .startedAt(started)
        .correlationId(correlation);
  }

  private MockAdapterScenario resolveScenario(UniversalAdapterRequest request) {
    JsonNode data = request.canonicalData();
    if (data != null && data.hasNonNull("mockScenario")) {
      try {
        return MockAdapterScenario.valueOf(data.get("mockScenario").asText().trim().toUpperCase());
      } catch (IllegalArgumentException ignored) {
        return MockAdapterScenario.INVALID_RESPONSE;
      }
    }
    return MockAdapterScenario.SUCCESS;
  }
}
