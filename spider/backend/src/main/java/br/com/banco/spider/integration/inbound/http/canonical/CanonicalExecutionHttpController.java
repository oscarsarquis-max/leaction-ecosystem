package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.application.canonical.GetCanonicalExecutionUseCase;
import br.com.banco.spider.application.canonical.ListCanonicalExecutionsUseCase;
import br.com.banco.spider.application.canonical.SubmitCanonicalExecutionUseCase;
import br.com.banco.spider.application.security.CanonicalIngressAuthenticationPort;
import br.com.banco.spider.application.security.CanonicalIngressSecurityContext;
import br.com.banco.spider.application.security.IngressAuthenticationRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.integration.inbound.http.canonical.dto.CanonicalExecutionHttpRequest;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/v1/canonical/executions")
@ConditionalOnProperty(name = "spider.canonical.http.enabled", havingValue = "true")
public class CanonicalExecutionHttpController {

  private static final Logger log = LoggerFactory.getLogger(CanonicalExecutionHttpController.class);

  private final CanonicalIngressAuthenticationPort authentication;
  private final SubmitCanonicalExecutionUseCase submitUseCase;
  private final GetCanonicalExecutionUseCase getUseCase;
  private final ListCanonicalExecutionsUseCase listUseCase;
  private final CanonicalExecutionHttpMapper mapper;
  private final CanonicalHttpStatusMapper statusMapper;
  private final SpiderClock clock;
  private final boolean statusQueryEnabled;

  public CanonicalExecutionHttpController(
      CanonicalIngressAuthenticationPort authentication,
      SubmitCanonicalExecutionUseCase submitUseCase,
      GetCanonicalExecutionUseCase getUseCase,
      ListCanonicalExecutionsUseCase listUseCase,
      CanonicalExecutionHttpMapper mapper,
      CanonicalHttpStatusMapper statusMapper,
      SpiderClock clock,
      br.com.banco.spider.config.CanonicalHttpProperties props) {
    this.authentication = authentication;
    this.submitUseCase = submitUseCase;
    this.getUseCase = getUseCase;
    this.listUseCase = listUseCase;
    this.mapper = mapper;
    this.statusMapper = statusMapper;
    this.clock = clock;
    this.statusQueryEnabled = props.isStatusQueryEnabled();
  }

  @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> list(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    if (!statusQueryEnabled) {
      return Mono.just(ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }
    IngressAuthenticationRequest authReq =
        new IngressAuthenticationRequest(
            "REST_HTTP",
            credentialRef,
            Map.of(),
            exchange.getRequest().getRemoteAddress() != null
                ? exchange.getRequest().getRemoteAddress().toString()
                : null,
            clock.now());
    return authentication
        .authenticate(authReq)
        .flatMap(
            opt -> {
              if (opt.isEmpty()) {
                log.info("event=authz_decision reasonCode=UNAUTHENTICATED path=list");
                return Mono.just(
                    ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body(Map.of("code", "UNAUTHENTICATED")));
              }
              return listUseCase
                  .listOwned(opt.get().principalRef(), 20)
                  .map(
                      items ->
                          ResponseEntity.ok()
                              .header("Cache-Control", "no-store")
                              .body(Map.of("items", items)));
            });
  }

  @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> submit(
      @RequestBody CanonicalExecutionHttpRequest body,
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
      @RequestHeader(value = "traceparent", required = false) String traceparent,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    log.info("event=canonical_http_request_received path=/v1/canonical/executions");
    IngressAuthenticationRequest authReq =
        new IngressAuthenticationRequest(
            "REST_HTTP",
            credentialRef,
            Map.of(),
            exchange.getRequest().getRemoteAddress() != null
                ? exchange.getRequest().getRemoteAddress().toString()
                : null,
            clock.now());
    return authentication
        .authenticate(authReq)
        .flatMap(
            opt -> {
              if (opt.isEmpty()) {
                log.info("event=authz_decision reasonCode=UNAUTHENTICATED");
                return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("code", "UNAUTHENTICATED")));
              }
              var originator = opt.get();
              CanonicalExecutionRequest canonical = mapper.toCanonical(body);
              var sec =
                  CanonicalIngressSecurityContext.from(
                      originator, br.com.banco.spider.application.security.AuthorizationDecision.PERMIT);
              TraceDescriptor transportTrace = null;
              boolean clientTrace =
                  Boolean.TRUE.equals(
                      exchange.getAttribute(br.com.banco.spider.web.filter.TraceContextWebFilter.CLIENT_PROVIDED_ATTR));
              if (clientTrace && traceparent != null) {
                transportTrace =
                    new TraceDescriptor(canonical.trace().correlationId(), traceparent, null);
              }
              return submitUseCase
                  .submit(
                      new SubmitCanonicalExecutionUseCase.SubmitCanonicalExecutionCommand(
                          canonical, sec, originator, transportTrace, idempotencyKey, clock.now()))
                  .map(
                      outcome -> {
                        if (!outcome.success()) {
                          HttpStatus status =
                              statusMapper.fromHint(outcome.httpHint(), outcome.error());
                          return ResponseEntity.status(status)
                              .body(Map.of("code", outcome.error().code(), "message", outcome.error().message()));
                        }
                        HttpStatus status = statusMapper.fromExecutionResult(outcome.result());
                        return ResponseEntity.status(status)
                            .header("Cache-Control", "no-store")
                            .body(outcome.result());
                      });
            });
  }

  @GetMapping(value = "/{executionId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> get(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    if (!statusQueryEnabled) {
      return Mono.just(ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }
    if (executionId == null || executionId.length() > 120) {
      return Mono.just(ResponseEntity.badRequest().body(Map.of("code", "INVALID_EXECUTION_ID")));
    }
    IngressAuthenticationRequest authReq =
        new IngressAuthenticationRequest(
            "REST_HTTP", credentialRef, Map.of(), null, clock.now());
    return authentication
        .authenticate(authReq)
        .flatMap(
            opt -> {
              if (opt.isEmpty()) {
                return Mono.just(
                    ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body(Map.of("code", "UNAUTHENTICATED")));
              }
              return getUseCase
                  .get(
                      new GetCanonicalExecutionUseCase.GetCanonicalExecutionQuery(
                          executionId, opt.get().principalRef(), null))
                  .map(
                      outcome -> {
                        if (!outcome.authorized()) {
                          return ResponseEntity.status(HttpStatus.FORBIDDEN)
                              .header("Cache-Control", "no-store")
                              .body(Map.of("code", "EXECUTION_NOT_VISIBLE"));
                        }
                        Object body =
                            outcome.result() != null
                                ? outcome.result()
                                : Map.of(
                                    "executionId",
                                    outcome.control().executionId(),
                                    "state",
                                    outcome.control().state().name());
                        return ResponseEntity.ok().header("Cache-Control", "no-store").body(body);
                      });
            });
  }
}
