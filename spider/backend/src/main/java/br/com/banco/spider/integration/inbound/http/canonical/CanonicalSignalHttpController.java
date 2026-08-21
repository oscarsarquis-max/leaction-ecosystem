package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.application.security.ExternalSignalIngressAuthenticationPort;
import br.com.banco.spider.application.security.IngressAuthenticationRequest;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.integration.inbound.http.canonical.dto.ExternalSignalHttpRequest;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/v1/canonical/signals")
@ConditionalOnProperty(name = "spider.canonical.signal-http.enabled", havingValue = "true")
public class CanonicalSignalHttpController {

  private static final Logger log = LoggerFactory.getLogger(CanonicalSignalHttpController.class);

  private final ExternalSignalIngressAuthenticationPort authentication;
  private final ExternalSignalHttpApplicationPort signalApp;
  private final CanonicalExecutionHttpMapper mapper;
  private final CanonicalHttpStatusMapper statusMapper;
  private final SpiderClock clock;

  public CanonicalSignalHttpController(
      ExternalSignalIngressAuthenticationPort authentication,
      ExternalSignalHttpApplicationPort signalApp,
      CanonicalExecutionHttpMapper mapper,
      CanonicalHttpStatusMapper statusMapper,
      SpiderClock clock) {
    this.authentication = authentication;
    this.signalApp = signalApp;
    this.mapper = mapper;
    this.statusMapper = statusMapper;
    this.clock = clock;
  }

  @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> receive(
      @RequestBody ExternalSignalHttpRequest body,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    log.info("event=canonical_http_request_received path=/v1/canonical/signals");
    if (body.messageId() == null || body.messageId().isBlank()) {
      return Mono.just(ResponseEntity.badRequest().body(Map.of("code", "MESSAGE_ID_REQUIRED")));
    }
    IngressAuthenticationRequest authReq =
        new IngressAuthenticationRequest(
            "REST_HTTP_SIGNAL", credentialRef, Map.of("sourceRef", body.sourceRef()), null, clock.now());
    return authentication
        .authenticate(authReq)
        .flatMap(
            opt -> {
              if (opt.isEmpty()) {
                log.info("event=signal_http_rejected reasonCode=UNAUTHENTICATED");
                return Mono.just(
                    ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body(Map.of("code", "UNAUTHENTICATED")));
              }
              var security = opt.get();
              if (!security.sourceRef().equals(body.sourceRef())) {
                log.info("event=signal_http_rejected reasonCode=SOURCE_MISMATCH");
                return Mono.just(
                    ResponseEntity.status(HttpStatus.FORBIDDEN)
                        .body(Map.of("code", "SOURCE_MISMATCH")));
              }
              var envelope = mapper.toEnvelope(body, security, clock.now());
              return signalApp
                  .handle(envelope)
                  .map(
                      result -> {
                        HttpStatus status = statusMapper.fromSignalStatus(result.processingStatus());
                        log.info(
                            "event=signal_http_accepted status={} reasonCode={}",
                            result.processingStatus(),
                            result.processingStatus());
                        return ResponseEntity.status(status)
                            .body(
                                Map.of(
                                    "processingStatus",
                                    result.processingStatus().name(),
                                    "executionId",
                                    result.executionId() == null ? "" : result.executionId()));
                      });
            });
  }
}
