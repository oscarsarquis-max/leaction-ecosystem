package br.com.banco.spider.orchestrator;

import br.com.banco.spider.domain.OrchestrationOutcome;
import br.com.banco.spider.domain.ProductOrchestrateRequest;
import br.com.banco.spider.engine.JwtTokenService;
import br.com.banco.spider.engine.mapper.LegacyPayloadTranslator;
import br.com.banco.spider.model.AuditTrace;
import br.com.banco.spider.model.ProductRoute;
import br.com.banco.spider.repository.AuditTraceRepository;
import br.com.banco.spider.repository.ProductRouteRepository;
import br.com.banco.spider.web.filter.TraceContextWebFilter;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.reactor.circuitbreaker.operator.CircuitBreakerOperator;
import io.github.resilience4j.reactor.retry.RetryOperator;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryRegistry;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class OrchestrationService {

  private static final Logger log = LoggerFactory.getLogger(OrchestrationService.class);
  private static final ParameterizedTypeReference<Map<String, Object>> MAP_TYPE =
      new ParameterizedTypeReference<>() {};

  private final ProductRouteRepository productRouteRepository;
  private final AuditTraceRepository auditTraceRepository;
  private final InMemoryRouteFallback inMemoryRouteFallback;
  private final LegacyPayloadTranslator translator;
  private final JwtTokenService jwtTokenService;
  private final ObjectMapper objectMapper;
  private final WebClient.Builder webClientBuilder;
  private final CircuitBreaker legadoCircuitBreaker;
  private final Retry legadoRetry;
  private final String defaultLegadoUrl;
  private final String originatorCallbackUrl;

  public OrchestrationService(
      ProductRouteRepository productRouteRepository,
      AuditTraceRepository auditTraceRepository,
      InMemoryRouteFallback inMemoryRouteFallback,
      LegacyPayloadTranslator translator,
      JwtTokenService jwtTokenService,
      ObjectMapper objectMapper,
      WebClient.Builder webClientBuilder,
      CircuitBreakerRegistry circuitBreakerRegistry,
      RetryRegistry retryRegistry,
      @Value("${spider.legado.base-url}") String legadoBaseUrl,
      @Value("${spider.legado.process-path}") String processPath,
      @Value("${spider.originator.base-url}") String originatorBaseUrl,
      @Value("${spider.originator.callback-path}") String callbackPath) {
    this.productRouteRepository = productRouteRepository;
    this.auditTraceRepository = auditTraceRepository;
    this.inMemoryRouteFallback = inMemoryRouteFallback;
    this.translator = translator;
    this.jwtTokenService = jwtTokenService;
    this.objectMapper = objectMapper;
    this.webClientBuilder = webClientBuilder;
    this.legadoCircuitBreaker = circuitBreakerRegistry.circuitBreaker("legadoFinanceiro");
    this.legadoRetry = retryRegistry.retry("legadoFinanceiro");
    this.defaultLegadoUrl = legadoBaseUrl + processPath;
    this.originatorCallbackUrl = originatorBaseUrl + callbackPath;
  }

  public Mono<OrchestrationOutcome> orchestrate(
      ProductOrchestrateRequest request, String traceparent) {
    Instant started = Instant.now();

    return resolveRoute(request.productId())
        .flatMap(
            route -> {
              String endpoint = resolveLegacyEndpoint(route);
              Map<String, Object> legadoBody = translator.toLegadoRequest(request, traceparent);
              log.info(
                  "Orchestrating productId={} endpoint={} traceparent={}",
                  request.productId(),
                  endpoint,
                  traceparent);

              return callLegado(endpoint, legadoBody, traceparent)
                  .map(legacy -> toOutcome(request, traceparent, started, legacy));
            })
        .doOnNext(this::persistAuditAsync)
        .doOnNext(this::notifyOriginatorAsync);
  }

  private OrchestrationOutcome toOutcome(
      ProductOrchestrateRequest request,
      String traceparent,
      Instant started,
      LegacyResponse legacy) {
    long latencyMs = Duration.between(started, Instant.now()).toMillis();
    boolean ok = legacy.httpStatus().is2xxSuccessful();
    String technicalStatus = ok ? mapTechnicalStatus(legacy.body()) : "FAILED";
    String jwtStatus = ok ? technicalStatus : "SUCCESS";
    String token =
        jwtTokenService.generateStateTransitionToken(
            request.transactionId(), request.productId(), jwtStatus, traceparent);

    return new OrchestrationOutcome(
        traceparent,
        request.productId(),
        request.transactionId(),
        technicalStatus,
        legacy.httpStatus().value(),
        latencyMs,
        token,
        legacy.body());
  }

  private Mono<ProductRoute> resolveRoute(String productId) {
    return Mono.fromCallable(
            () ->
                productRouteRepository
                    .findFirstByProductCodeAndEnabledTrueOrderByVersionDesc(productId)
                    .or(() -> inMemoryRouteFallback.find(productId))
                    .orElseThrow(
                        () ->
                            new IllegalStateException(
                                "Nenhuma rota ativa para productId=" + productId)))
        .subscribeOn(Schedulers.boundedElastic());
  }

  private String resolveLegacyEndpoint(ProductRoute route) {
    try {
      JsonNode node = objectMapper.readTree(route.getDefinitionJson());
      if (node.hasNonNull("legacyEndpoint")) {
        return node.get("legacyEndpoint").asText();
      }
    } catch (JsonProcessingException ignored) {
      // fallback below
    }
    return defaultLegadoUrl;
  }

  private Mono<LegacyResponse> callLegado(
      String endpoint, Map<String, Object> body, String traceparent) {
    Mono<LegacyResponse> call =
        webClientBuilder
            .build()
            .post()
            .uri(endpoint)
            .header(TraceContextWebFilter.TRACEPARENT_HEADER, traceparent)
            .bodyValue(body)
            .exchangeToMono(this::toLegacyResponse);

    return call
        .transformDeferred(RetryOperator.of(legadoRetry))
        .transformDeferred(CircuitBreakerOperator.of(legadoCircuitBreaker));
  }

  private Mono<LegacyResponse> toLegacyResponse(ClientResponse response) {
    HttpStatusCode status = response.statusCode();
    return response
        .bodyToMono(MAP_TYPE)
        .defaultIfEmpty(Map.of())
        .map(body -> new LegacyResponse(status, body));
  }

  private String mapTechnicalStatus(Map<String, Object> body) {
    Object st = body == null ? null : body.get("status");
    if (st != null && String.valueOf(st).toUpperCase().contains("PAYMENT")) {
      return "PAYMENT_CONFIRMED";
    }
    return "SUCCESS";
  }

  private void persistAuditAsync(OrchestrationOutcome outcome) {
    Mono.fromCallable(
            () -> {
              Map<String, Object> meta = new HashMap<>();
              meta.put("traceparent", outcome.traceparent());
              meta.put("httpStatus", outcome.legacyHttpStatus());
              meta.put("latencyMs", outcome.latencyMs());
              meta.put("transactionId", outcome.transactionId());

              AuditTrace trace =
                  AuditTrace.builder()
                      .correlationId(traceIdAsUuid(outcome.traceparent()))
                      .productCode(outcome.productId())
                      .idempotencyKey(outcome.transactionId())
                      .status(outcome.technicalStatus())
                      .startedAt(Instant.now().minusMillis(outcome.latencyMs()))
                      .finishedAt(Instant.now())
                      .errorSummary(
                          outcome.legacyHttpStatus() >= 400
                              ? "legacy_http_" + outcome.legacyHttpStatus()
                              : null)
                      .metadata(writeJson(meta))
                      .build();
              return auditTraceRepository.save(trace);
            })
        .subscribeOn(Schedulers.boundedElastic())
        .subscribe(
            saved -> log.debug("Audit persisted id={}", saved.getId()),
            err -> log.warn("Audit persistence failed: {}", err.toString()));
  }

  private void notifyOriginatorAsync(OrchestrationOutcome outcome) {
    Map<String, Object> callbackBody =
        Map.of(
            "traceparent", outcome.traceparent(),
            "productId", outcome.productId(),
            "transactionId", outcome.transactionId(),
            "status_tecnico", outcome.technicalStatus(),
            "stateTransitionToken", outcome.stateTransitionToken());

    webClientBuilder
        .build()
        .post()
        .uri(originatorCallbackUrl)
        .header(TraceContextWebFilter.TRACEPARENT_HEADER, outcome.traceparent())
        .bodyValue(callbackBody)
        .retrieve()
        .toBodilessEntity()
        .subscribe(
            ok -> log.info("Originator callback OK status={}", ok.getStatusCode()),
            err -> log.warn("Originator callback failed: {}", err.toString()));
  }

  private UUID traceIdAsUuid(String traceparent) {
    try {
      String traceId = traceparent.split("-")[1];
      return UUID.fromString(
          traceId.substring(0, 8)
              + "-"
              + traceId.substring(8, 12)
              + "-"
              + traceId.substring(12, 16)
              + "-"
              + traceId.substring(16, 20)
              + "-"
              + traceId.substring(20, 32));
    } catch (Exception e) {
      return UUID.randomUUID();
    }
  }

  private String writeJson(Map<String, Object> map) {
    try {
      return objectMapper.writeValueAsString(map);
    } catch (JsonProcessingException e) {
      return "{}";
    }
  }

  private record LegacyResponse(HttpStatusCode httpStatus, Map<String, Object> body) {}
}
