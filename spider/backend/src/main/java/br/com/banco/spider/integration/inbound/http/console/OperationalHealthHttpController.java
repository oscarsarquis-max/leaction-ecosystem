package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.operational.health.OperationalHealthQueryService;
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

@RestController
@RequestMapping("/v1/console/operational-health")
@ConditionalOnProperty(
    name = {"spider.console.http.enabled", "spider.operational-health.enabled"},
    havingValue = "true")
public class OperationalHealthHttpController {
  private final OperationalConsoleAuthenticationPort authentication;
  private final OperationalConsoleAuthorizationPort authorization;
  private final OperationalHealthQueryService queryService;

  public OperationalHealthHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      OperationalHealthQueryService queryService) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
  }

  @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> snapshot(
      @RequestParam(required = false) String window,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(
            allowed -> {
              if (!allowed) {
                return denied();
              }
              try {
                return ResponseEntity.ok()
                    .cacheControl(CacheControl.noStore())
                    .<Object>body(queryService.getSnapshot(window));
              } catch (IllegalArgumentException invalid) {
                return ResponseEntity.badRequest()
                    .cacheControl(CacheControl.noStore())
                    .body(Map.of("title", "Invalid operational health window", "status", 400));
              }
            });
  }

  @GetMapping(value = "/definitions", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> definitions(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef)
        .map(
            allowed ->
                allowed
                    ? ResponseEntity.ok()
                        .cacheControl(CacheControl.noStore())
                        .<Object>body(queryService.definitions())
                    : denied());
  }

  private Mono<Boolean> authorize(String credentialRef) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            context ->
                context.authenticated()
                    ? authorization.authorize(
                        context, OperationalConsoleAction.VIEW_OPERATIONAL_HEALTH)
                    : Mono.just(false));
  }

  private static ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }
}
