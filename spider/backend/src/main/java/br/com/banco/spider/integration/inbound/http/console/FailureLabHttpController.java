package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.operational.failurelab.FailureLabOrchestrator;
import br.com.banco.spider.operational.failurelab.FailureLabQueryService;
import br.com.banco.spider.operational.failurelab.FailureLabRejectedException;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.CacheControl;
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
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/v1/console/failure-lab")
@ConditionalOnProperty(
    name = {
      "spider.console.http.enabled",
      "spider.failure-lab.enabled",
      "spider.failure-lab.http.enabled"
    },
    havingValue = "true")
public class FailureLabHttpController {

  private final OperationalConsoleAuthenticationPort authentication;
  private final OperationalConsoleAuthorizationPort authorization;
  private final FailureLabQueryService queryService;
  private final FailureLabOrchestrator orchestrator;

  public FailureLabHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      FailureLabQueryService queryService,
      FailureLabOrchestrator orchestrator) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
    this.orchestrator = orchestrator;
  }

  public record StartRunRequest(
      String scenarioCode, String scenarioVersion, Map<String, String> parameters) {}

  @GetMapping(value = "/scenarios", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> scenarios(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_FAILURE_LAB)
        .map(
            allowed ->
                allowed
                    ? ResponseEntity.ok()
                        .cacheControl(CacheControl.noStore())
                        .<Object>body(queryService.listScenarios())
                    : denied());
  }

  @PostMapping(
      value = "/runs",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> startRun(
      @RequestBody StartRunRequest request,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            context -> {
              if (!context.authenticated()) {
                return Mono.just(denied());
              }
              return authorization
                  .authorize(context, OperationalConsoleAction.EXECUTE_MOCK_FAILURE_SCENARIO)
                  .flatMap(
                      allowed -> {
                        if (!allowed) {
                          return Mono.just(denied());
                        }
                        if (request == null
                            || request.scenarioCode() == null
                            || request.scenarioCode().isBlank()) {
                          return Mono.just(
                              problem(HttpStatus.BAD_REQUEST, "scenarioCode is required"));
                        }
                        return orchestrator
                            .startRun(
                                request.scenarioCode(),
                                request.scenarioVersion(),
                                request.parameters(),
                                context.principalRef())
                            .<ResponseEntity<?>>map(
                                run ->
                                    ResponseEntity.accepted()
                                        .cacheControl(CacheControl.noStore())
                                        .body(run))
                            .onErrorResume(
                                FailureLabRejectedException.class,
                                rejected -> Mono.just(rejection(rejected)));
                      });
            });
  }

  @GetMapping(value = "/runs/{labRunId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> run(
      @PathVariable String labRunId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_FAILURE_LAB)
        .map(
            allowed -> {
              if (!allowed) {
                return denied();
              }
              return queryService
                  .getRun(labRunId)
                  .<ResponseEntity<?>>map(
                      run ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .body(run))
                  .orElseGet(FailureLabHttpController::denied);
            });
  }

  @GetMapping(value = "/runs/{labRunId}/evidence", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> evidence(
      @PathVariable String labRunId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    return authorize(credentialRef, OperationalConsoleAction.VIEW_FAILURE_LAB_EVIDENCE)
        .map(
            allowed -> {
              if (!allowed) {
                return denied();
              }
              return queryService
                  .getEvidence(labRunId)
                  .<ResponseEntity<?>>map(
                      bundle ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .body(bundle))
                  .orElseGet(FailureLabHttpController::denied);
            });
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

  private static ResponseEntity<?> rejection(FailureLabRejectedException rejected) {
    return switch (rejected.reasonCode()) {
      case FailureLabRejectedException.DISABLED, FailureLabRejectedException.SCENARIO_NOT_FOUND ->
          denied();
      case FailureLabRejectedException.PARAMETER_NOT_ALLOWED ->
          problem(HttpStatus.BAD_REQUEST, rejected.reasonCode());
      case FailureLabRejectedException.CONCURRENCY_LIMIT_REACHED ->
          problem(HttpStatus.CONFLICT, rejected.reasonCode());
      default -> problem(HttpStatus.CONFLICT, rejected.reasonCode());
    };
  }

  private static ResponseEntity<?> problem(HttpStatus status, String title) {
    return ResponseEntity.status(status)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", title, "status", status.value()));
  }

  private static ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }
}
