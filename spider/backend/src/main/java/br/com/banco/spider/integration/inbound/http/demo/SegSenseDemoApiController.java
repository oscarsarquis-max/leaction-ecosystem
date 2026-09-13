package br.com.banco.spider.integration.inbound.http.demo;

import br.com.banco.spider.config.SegSenseDemoProperties;
import br.com.banco.spider.demo.segsense.SegSenseDemoApplicationAuth;
import br.com.banco.spider.demo.segsense.SegSenseDemoDecisionService;
import br.com.banco.spider.demo.segsense.SegSenseDemoDecisionService.Command;
import br.com.banco.spider.demo.segsense.SegSenseDemoDecisionService.Decision;
import br.com.banco.spider.demo.segsense.SegSenseDemoOriginSnapshot;
import java.nio.charset.StandardCharsets;
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
@ConditionalOnBean(SegSenseDemoDecisionService.class)
public class SegSenseDemoApiController {

  private static final Logger log = LoggerFactory.getLogger(SegSenseDemoApiController.class);

  private final SegSenseDemoDecisionService decisions;
  private final SegSenseDemoProperties properties;
  private final SegSenseDemoApplicationAuth auth;

  public SegSenseDemoApiController(
      SegSenseDemoDecisionService decisions, SegSenseDemoProperties properties) {
    this.decisions = decisions;
    this.properties = properties;
    this.auth = new SegSenseDemoApplicationAuth(properties);
  }

  @PostMapping(
      path = "/v1/demo/segsense/protection-decisions",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> decide(
      ServerWebExchange exchange,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      @RequestHeader(value = SegSenseDemoApplicationAuth.SECRET_HEADER, required = false)
          String applicationSecret,
      @RequestHeader(value = "X-Correlation-ID", required = false) String correlationId,
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
      @RequestBody(required = false) Map<String, Object> body) {
    if (auth.remoteForbidden(exchange)) {
      return Mono.just(
          ResponseEntity.status(403)
              .header("Cache-Control", "no-store")
              .body(Map.of("code", "ACCESS_DENIED", "message", "A fatia de demonstração não está exposta.")));
    }
    if (!auth.authenticated(credentialRef, applicationSecret)) {
      return Mono.just(
          ResponseEntity.status(401)
              .header("Cache-Control", "no-store")
              .body(Map.of("code", "AUTHENTICATION_REQUIRED", "message", "Autenticação de aplicação necessária.")));
    }
    if (body != null
        && body.toString().getBytes(StandardCharsets.UTF_8).length > properties.getMaxBytes()) {
      return Mono.just(
          ResponseEntity.status(400)
              .header("Cache-Control", "no-store")
              .body(Map.of("code", "VALIDATION_ERROR", "message", "Pedido excede o limite.")));
    }
    Command command =
        new Command(
            string(body, "contractVersion"),
            string(body, "applicationId"),
            string(body, "scenarioKey"),
            body == null ? null : SegSenseDemoOriginSnapshot.parse(body.get("originSnapshot")),
            string(body, "declaredObjective"),
            correlationId,
            idempotencyKey);
    return decisions
        .decide(command)
        .doOnNext(
            decision ->
                log.info(
                    "event=segsense_demo_decision status={} http={} correlationId={} decisionId={}",
                    decision.body() == null ? decision.errorCode() : decision.body().get("status"),
                    decision.status(),
                    correlationId,
                    decision.body() == null ? null : decision.body().get("decisionId")))
        .map(SegSenseDemoApiController::toResponse);
  }

  private static ResponseEntity<?> toResponse(Decision decision) {
    if (decision.status() == 200) {
      return ResponseEntity.ok().header("Cache-Control", "no-store").body(decision.body());
    }
    return ResponseEntity.status(decision.status())
        .header("Cache-Control", "no-store")
        .body(Map.of("code", decision.errorCode(), "message", decision.message()));
  }

  private static String string(Map<String, Object> body, String key) {
    if (body == null) {
      return null;
    }
    Object value = body.get(key);
    return value == null ? null : String.valueOf(value);
  }
}
