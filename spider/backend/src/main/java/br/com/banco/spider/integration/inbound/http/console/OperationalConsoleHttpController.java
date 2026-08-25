package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.GetImplementationStatusUseCase;
import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleQueryService;
import br.com.banco.spider.application.console.PresentationReadinessUseCase;
import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.operational.readmodel.ListOperationalExecutionsQuery;
import br.com.banco.spider.operational.readmodel.OperationalExecutionDetail;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/v1/console")
@ConditionalOnProperty(name = "spider.console.http.enabled", havingValue = "true")
public class OperationalConsoleHttpController {

  private final OperationalConsoleAuthenticationPort authentication;
  private final OperationalConsoleAuthorizationPort authorization;
  private final OperationalConsoleQueryService queryService;
  private final GetImplementationStatusUseCase implementationStatus;
  private final PresentationReadinessUseCase presentationReadiness;
  private final OperationalConsoleProperties props;

  public OperationalConsoleHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      OperationalConsoleQueryService queryService,
      GetImplementationStatusUseCase implementationStatus,
      PresentationReadinessUseCase presentationReadiness,
      OperationalConsoleProperties props) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
    this.implementationStatus = implementationStatus;
    this.presentationReadiness = presentationReadiness;
    this.props = props;
  }

  @GetMapping(value = "/executions", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> list(
      @RequestParam(required = false) String states,
      @RequestParam(required = false) String routeCode,
      @RequestParam(required = false) Instant startedFrom,
      @RequestParam(required = false) Instant startedTo,
      @RequestParam(required = false, defaultValue = "false") boolean onlyWaiting,
      @RequestParam(required = false) Instant cursorStartedAt,
      @RequestParam(required = false) String cursorExecutionId,
      @RequestParam(required = false) Integer limit,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return authenticateAndAuthorize(credentialRef, OperationalConsoleAction.LIST_EXECUTIONS)
        .flatMap(
            allowed -> {
              if (!allowed) {
                return Mono.just(denied());
              }
              List<ExecutionState> stateList = parseStates(states);
              int lim =
                  limit == null
                      ? props.getDefaultPageSize()
                      : Math.min(limit, props.getMaxPageSize());
              ListOperationalExecutionsQuery q =
                  new ListOperationalExecutionsQuery(
                      stateList,
                      routeCode,
                      startedFrom,
                      startedTo,
                      onlyWaiting,
                      cursorStartedAt,
                      cursorExecutionId,
                      lim);
              return queryService
                  .list(q)
                  .map(
                      page ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .body(
                                  Map.of(
                                      "items",
                                      page.items(),
                                      "nextCursorStartedAt",
                                      page.nextCursorStartedAt() == null
                                          ? ""
                                          : page.nextCursorStartedAt(),
                                      "nextCursorExecutionId",
                                      page.nextCursorExecutionId() == null
                                          ? ""
                                          : page.nextCursorExecutionId(),
                                      "pollingMinInterval",
                                      props.getPollingMinInterval().toString())));
            });
  }

  @GetMapping(value = "/executions/{executionId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> detail(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return authenticateAndAuthorize(credentialRef, OperationalConsoleAction.VIEW_EXECUTION_SUMMARY)
        .flatMap(
            allowed -> {
              if (!allowed) {
                return Mono.just(denied());
              }
              return queryService
                  .getDetail(executionId)
                  .map(
                      opt -> {
                        if (opt.isEmpty()) {
                          return denied();
                        }
                        OperationalExecutionDetail d = opt.get();
                        return ResponseEntity.ok()
                            .cacheControl(CacheControl.noStore())
                            .<Object>body(d);
                      });
            });
  }

  @GetMapping(value = "/executions/{executionId}/events", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> operationalEvents(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return authenticateAndAuthorize(credentialRef, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)
        .flatMap(
            allowed -> {
              if (!allowed) {
                return Mono.just(denied());
              }
              return queryService
                  .listOperationalEvents(executionId)
                  .map(
                      items ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .<Object>body(
                                  Map.of("executionId", executionId, "items", items)));
            });
  }

  @GetMapping(value = "/implementation", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> implementation(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return authenticateAndAuthorize(
            credentialRef, OperationalConsoleAction.VIEW_IMPLEMENTATION_STATUS)
        .flatMap(
            allowed -> {
              if (!allowed) {
                return Mono.just(denied());
              }
              return implementationStatus
                  .execute()
                  .map(
                      body ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .<Object>body(body));
            });
  }

  @GetMapping(value = "/presentation/readiness", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> presentationReadiness(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    return authenticateAndAuthorize(
            credentialRef, OperationalConsoleAction.VIEW_PRESENTATION_READINESS)
        .flatMap(
            allowed -> {
              if (!allowed) {
                return Mono.just(denied());
              }
              return presentationReadiness
                  .execute()
                  .map(
                      body ->
                          ResponseEntity.ok()
                              .cacheControl(CacheControl.noStore())
                              .<Object>body(body));
            });
  }

  private Mono<Boolean> authenticateAndAuthorize(
      String credentialRef, OperationalConsoleAction action) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            ctx -> {
              if (!ctx.authenticated()) {
                return Mono.just(false);
              }
              return authorization.authorize(ctx, action);
            });
  }

  private static ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }

  private static List<ExecutionState> parseStates(String states) {
    if (states == null || states.isBlank()) {
      return List.of();
    }
    return Arrays.stream(states.split(","))
        .map(String::trim)
        .filter(s -> !s.isEmpty())
        .map(ExecutionState::valueOf)
        .toList();
  }
}
