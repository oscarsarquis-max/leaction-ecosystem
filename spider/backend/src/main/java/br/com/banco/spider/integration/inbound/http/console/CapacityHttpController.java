package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.operational.capacity.CapacityQueryService;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

/**
 * Leitura operacional do governo de capacidade. Negação responde 404 — a borda não confirma que
 * existe política, escopo ou decisão para enumerar.
 */
@RestController
@RequestMapping("/v1/console/capacity")
@ConditionalOnProperty(
    name = {"spider.console.http.enabled", "spider.capacity.enabled", "spider.capacity.http.enabled"},
    havingValue = "true")
public class CapacityHttpController {

  private static final int MAX_DECISION_PAGE = 200;

  private final OperationalConsoleAuthenticationPort authentication;
  private final OperationalConsoleAuthorizationPort authorization;
  private final CapacityQueryService queryService;

  public CapacityHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      CapacityQueryService queryService) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
  }

  @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> snapshot(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef).map(allowed -> allowed ? ok(queryService.getSnapshot()) : denied());
  }

  @GetMapping(value = "/policies", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> policies(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(allowed -> allowed ? ok(Map.of("policies", queryService.policies())) : denied());
  }

  @GetMapping(value = "/pressure", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> pressure(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(allowed -> allowed ? ok(Map.of("pressure", queryService.pressure())) : denied());
  }

  @GetMapping(value = "/bulkheads", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> bulkheads(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(allowed -> allowed ? ok(Map.of("bulkheads", queryService.bulkheads())) : denied());
  }

  @GetMapping(value = "/circuits", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> circuits(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(allowed -> allowed ? ok(Map.of("circuits", queryService.circuits())) : denied());
  }

  @GetMapping(value = "/decisions", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> decisions(
      @RequestParam(value = "limit", required = false) Integer limit,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    int effective = limit == null ? MAX_DECISION_PAGE : Math.min(Math.max(limit, 1), MAX_DECISION_PAGE);
    return authorize(credentialRef)
        .map(
            allowed ->
                allowed
                    ? ok(Map.of("decisions", queryService.decisions(effective)))
                    : denied());
  }

  private Mono<Boolean> authorize(String credentialRef) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            context ->
                context.authenticated()
                    ? authorization.authorize(context, OperationalConsoleAction.VIEW_CAPACITY)
                    : Mono.just(false));
  }

  private static ResponseEntity<?> ok(Object body) {
    return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(body);
  }

  private static ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }
}
