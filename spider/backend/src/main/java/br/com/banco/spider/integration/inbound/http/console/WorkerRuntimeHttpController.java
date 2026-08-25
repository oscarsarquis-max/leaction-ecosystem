package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.config.WorkerRuntimeProperties;
import br.com.banco.spider.operational.workers.RequestWorkerDrainUseCase;
import br.com.banco.spider.operational.workers.WorkerRuntimeQueryService;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

/**
 * Leitura operacional do runtime de workers. Negação e recurso inexistente respondem 404 — a borda
 * não enumera workers nem revela que um identificador existe.
 */
@RestController
@RequestMapping("/v1/console/runtime")
@ConditionalOnProperty(
    name = {
      "spider.console.http.enabled",
      "spider.worker-runtime.enabled",
      "spider.worker-runtime.http.enabled"
    },
    havingValue = "true")
public class WorkerRuntimeHttpController {

  private final OperationalConsoleAuthenticationPort authentication;
  private final OperationalConsoleAuthorizationPort authorization;
  private final WorkerRuntimeQueryService queryService;
  private final RequestWorkerDrainUseCase drainUseCase;
  private final WorkerRuntimeProperties properties;

  public WorkerRuntimeHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      WorkerRuntimeQueryService queryService,
      RequestWorkerDrainUseCase drainUseCase,
      WorkerRuntimeProperties properties) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
    this.drainUseCase = drainUseCase;
    this.properties = properties;
  }

  @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> snapshot(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_WORKER_RUNTIME)
        .map(allowed -> allowed ? ok(queryService.getSnapshot()) : denied());
  }

  @GetMapping(value = "/workers", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> workers(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_WORKER_RUNTIME)
        .map(allowed -> allowed ? ok(Map.of("workers", queryService.workers())) : denied());
  }

  @GetMapping(value = "/workers/{workerId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> worker(
      @PathVariable String workerId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_WORKER_RUNTIME)
        .map(
            allowed -> {
              if (!allowed) {
                return denied();
              }
              return queryService
                  .worker(workerId)
                  .<ResponseEntity<?>>map(WorkerRuntimeHttpController::ok)
                  .orElseGet(WorkerRuntimeHttpController::denied);
            });
  }

  @GetMapping(value = "/schedules", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> schedules(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_WORKER_RUNTIME)
        .map(allowed -> allowed ? ok(Map.of("schedules", queryService.schedules())) : denied());
  }

  @GetMapping(value = "/backlogs", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> backlogs(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_WORKER_RUNTIME)
        .map(allowed -> allowed ? ok(Map.of("backlogs", queryService.backlogs())) : denied());
  }

  @PostMapping(value = "/workers/{workerId}/drain", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> drain(
      @PathVariable String workerId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            context -> {
              if (!context.authenticated()) {
                return Mono.just(denied());
              }
              return authorization
                  .authorize(context, OperationalConsoleAction.DRAIN_WORKER)
                  .map(
                      allowed -> {
                        if (!allowed || !drainAllowed()) {
                          return denied();
                        }
                        return drainUseCase
                            .requestDrain(workerId, context.principalRef())
                            .<ResponseEntity<?>>map(WorkerRuntimeHttpController::accepted)
                            .orElseGet(WorkerRuntimeHttpController::denied);
                      });
            });
  }

  private boolean drainAllowed() {
    return properties.isAllowDrain() || properties.getLocalDemo().isEnabled();
  }

  private Mono<Boolean> authorize(String credentialRef, OperationalConsoleAction action) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            context ->
                context.authenticated()
                    ? authorization.authorize(context, action)
                    : Mono.just(false));
  }

  private static ResponseEntity<?> ok(Object body) {
    return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(body);
  }

  private static ResponseEntity<?> accepted(Object body) {
    return ResponseEntity.accepted().cacheControl(CacheControl.noStore()).body(body);
  }

  private static ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }
}
