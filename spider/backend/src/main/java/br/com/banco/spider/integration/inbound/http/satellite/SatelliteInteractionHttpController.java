package br.com.banco.spider.integration.inbound.http.satellite;

import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import br.com.banco.spider.satellite.application.SatelliteInteractionService.Outcome;
import br.com.banco.spider.satellite.contract.SatelliteContractSchema;
import br.com.banco.spider.satellite.contract.SatelliteInteractionParser;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import io.swagger.v3.oas.annotations.Operation;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@RestController
@Profile("local-demo")
@ConditionalOnBean(SatelliteInteractionService.class)
public class SatelliteInteractionHttpController {

  private static final Logger log = LoggerFactory.getLogger(SatelliteInteractionHttpController.class);

  private final SatelliteInteractionService interactions;
  private final SatelliteApplicationAuth auth;
  private final SatelliteContractProperties properties;

  public SatelliteInteractionHttpController(
      SatelliteInteractionService interactions,
      SatelliteApplicationAuth auth,
      SatelliteContractProperties properties) {
    this.interactions = interactions;
    this.auth = auth;
    this.properties = properties;
  }

  @Operation(summary = "Satellite Contract V1 interaction (EXPERIENCE)")
  @PostMapping(
      path = "/v1/satellites/interactions",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> interact(
      ServerWebExchange exchange,
      @RequestHeader(value = SatelliteApplicationAuth.SATELLITE_ID_HEADER, required = false)
          String satelliteId,
      @RequestHeader(value = SatelliteApplicationAuth.SATELLITE_SECRET_HEADER, required = false)
          String secret,
      @RequestHeader(value = "X-Correlation-ID", required = false) String correlationHeader,
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyHeader,
      @RequestBody(required = false) Map<String, Object> body) {
    if (SatelliteLoopbackGuard.remoteForbidden(exchange, properties.isLoopbackOnly())) {
      return Mono.just(error(403, "UNAUTHORIZED_SATELLITE", "A fatia de demonstração não está exposta.", null));
    }
    String authenticated = auth.authenticate(satelliteId, secret);
    if (authenticated == null) {
      return Mono.just(
          error(401, "UNAUTHENTICATED", "Autenticação de satélite necessária.", correlationHeader));
    }
    if (body != null && body.toString().getBytes(StandardCharsets.UTF_8).length > properties.getMaxBytes()) {
      return Mono.just(error(400, "INVALID_PAYLOAD", "Pedido excede o limite.", correlationHeader));
    }
    Map<String, Object> payload = body == null ? Map.of() : new LinkedHashMap<>(body);
    if (correlationHeader != null && !correlationHeader.isBlank()) {
      payload.putIfAbsent("correlationId", correlationHeader);
    }
    if (idempotencyHeader != null && !idempotencyHeader.isBlank()) {
      payload.putIfAbsent("idempotencyKey", idempotencyHeader);
    }
    String schemaError = SatelliteContractSchema.validateRequest(payload);
    if (schemaError != null) {
      return Mono.just(error(400, "INVALID_PAYLOAD", "Envelope canônico inválido.", correlationHeader));
    }
    SatelliteInteractionRequest request = SatelliteInteractionParser.parse(payload);
    return interactions
        .interact(authenticated, request)
        .doOnNext(
            outcome ->
                log.info(
                    "event=satellite_interaction satelliteId={} role={} correlationId={} status={} http={}",
                    authenticated,
                    request.satelliteRole(),
                    request.correlationId(),
                    outcome.body() == null ? outcome.errorCode() : outcome.body().get("status"),
                    outcome.status()))
        .map(SatelliteInteractionHttpController::toResponse);
  }

  private static ResponseEntity<?> toResponse(Outcome outcome) {
    if (outcome.status() == 200) {
      return ResponseEntity.ok().header("Cache-Control", "no-store").body(canonicalBody(outcome.body()));
    }
    return ResponseEntity.status(outcome.status())
        .header("Cache-Control", "no-store")
        .body(outcome.body());
  }

  private static Map<String, Object> canonicalBody(Map<String, Object> body) {
    Map<String, Object> canonical = new LinkedHashMap<>();
    for (String key :
        new String[] {
          "contractVersion",
          "decisionId",
          "status",
          "requiredAction",
          "resultSummary",
          "missingContext",
          "nextInteraction",
          "correlationId",
          "contextRef",
          "explainabilityRef",
          "watermark",
          "explanation",
          "originProvenance",
          "spiderPath",
          "capabilityId",
          "providerRequestId"
        }) {
      if (body.containsKey(key)) {
        canonical.put(key, body.get(key));
      }
    }
    return canonical;
  }

  private static ResponseEntity<Map<String, Object>> error(
      int status, String code, String message, String correlationId) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("errorCode", code);
    body.put("message", message);
    body.put("correlationId", correlationId);
    body.put("retryable", false);
    return ResponseEntity.status(status).header("Cache-Control", "no-store").body(body);
  }
}
