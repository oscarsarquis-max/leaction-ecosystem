package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.GetImplementationStatusUseCase;
import br.com.banco.spider.application.console.MonitorCompanyAccess;
import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleQueryService;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.application.console.PresentationReadinessUseCase;
import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.operational.readmodel.ListOperationalExecutionsQuery;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.readmodel.OperationalExecutionDetail;
import br.com.banco.spider.operational.readmodel.OperationalExecutionListItem;
import java.time.Instant;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;
import reactor.core.publisher.Flux;
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
  private final MonitorCompanyAccess companyAccess;

  public OperationalConsoleHttpController(
      OperationalConsoleAuthenticationPort authentication,
      OperationalConsoleAuthorizationPort authorization,
      OperationalConsoleQueryService queryService,
      GetImplementationStatusUseCase implementationStatus,
      PresentationReadinessUseCase presentationReadiness,
      OperationalConsoleProperties props,
      MonitorCompanyAccess companyAccess) {
    this.authentication = authentication;
    this.authorization = authorization;
    this.queryService = queryService;
    this.implementationStatus = implementationStatus;
    this.presentationReadiness = presentationReadiness;
    this.props = props;
    this.companyAccess = companyAccess;
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
    Mono<ResponseEntity<?>> listed =
        authorizedContext(credentialRef, OperationalConsoleAction.LIST_EXECUTIONS)
            .flatMap(
                ctx -> {
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
                      .flatMap(page -> visibleItems(ctx, page.items()))
                      .map(
                          items ->
                              okBody(
                                  Map.of(
                                      "items",
                                      items,
                                      "nextCursorStartedAt",
                                      "",
                                      "nextCursorExecutionId",
                                      "",
                                      "pollingMinInterval",
                                      props.getPollingMinInterval().toString())));
                });
    return listed.switchIfEmpty(Mono.fromSupplier(this::denied));
  }

  @GetMapping(value = "/executions/{executionId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> detail(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    Mono<ResponseEntity<?>> detailed =
        authorizedContext(credentialRef, OperationalConsoleAction.VIEW_EXECUTION_SUMMARY)
            .flatMap(ctx -> requireVisibleExecution(ctx, executionId))
            .flatMap(
                ignored ->
                    queryService
                        .getDetail(executionId)
                        .map(
                            opt -> {
                              if (opt.isEmpty()) {
                                return denied();
                              }
                              return okBody(opt.get());
                            }));
    return detailed.switchIfEmpty(Mono.fromSupplier(this::denied));
  }

  @GetMapping(value = "/executions/{executionId}/events", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> operationalEvents(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) {
      return Mono.just(ResponseEntity.notFound().build());
    }
    Mono<ResponseEntity<?>> events =
        authorizedContext(credentialRef, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)
            .flatMap(ctx -> requireVisibleExecution(ctx, executionId))
            .map(items -> okBody(Map.of("executionId", executionId, "items", items)));
    return events.switchIfEmpty(Mono.fromSupplier(this::denied));
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

  @GetMapping(value = "/monitor/simulation", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> simulationReadiness(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) return Mono.just(ResponseEntity.notFound().build());
    return authenticateAndAuthorize(credentialRef, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)
        .flatMap(allowed -> {
          if (!allowed) return Mono.just(denied());
          return queryService.simulationReadiness().map(body ->
              ResponseEntity.ok().cacheControl(CacheControl.noStore()).<Object>body(body));
        });
  }

  @GetMapping(value = "/monitor/events", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> monitorEvents(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef) {
    if (!props.isEnabled()) return Mono.just(ResponseEntity.notFound().build());
    Mono<ResponseEntity<?>> monitored =
        authorizedContext(credentialRef, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)
            .flatMap(
                ctx ->
                    queryService
                        .monitorEvents()
                        .map(
                            body -> {
                              Object raw = body.get("items");
                              if (companyAccess.enabled() && raw instanceof List<?> items) {
                                List<OperationalEvent> events =
                                    items.stream()
                                        .filter(OperationalEvent.class::isInstance)
                                        .map(OperationalEvent.class::cast)
                                        .toList();
                                Map<String, List<OperationalEvent>> byExecution =
                                    events.stream().collect(Collectors.groupingBy(OperationalEvent::executionId));
                                Set<String> visible =
                                    byExecution.entrySet().stream()
                                        .filter(
                                            entry ->
                                                companyAccess.maySee(
                                                    ctx,
                                                    companyAccess.companyOfEvents(entry.getValue()),
                                                    companyAccess.looksCanonicalEvents(entry.getValue())))
                                        .map(Map.Entry::getKey)
                                        .collect(Collectors.toSet());
                                List<OperationalEvent> filtered =
                                    events.stream()
                                        .filter(event -> visible.contains(event.executionId()))
                                        .toList();
                                Map<String, Object> copy = new LinkedHashMap<>(body);
                                copy.put("items", filtered);
                                return okBody(copy);
                              }
                              return okBody(body);
                            }));
    return monitored.switchIfEmpty(Mono.fromSupplier(this::denied));
  }

  private Mono<OperationalConsoleSecurityContext> authorizedContext(
      String credentialRef, OperationalConsoleAction action) {
    return authentication
        .authenticate(credentialRef)
        .flatMap(
            ctx -> {
              if (!ctx.authenticated()) {
                return Mono.empty();
              }
              return authorization.authorize(ctx, action).flatMap(ok -> ok ? Mono.just(ctx) : Mono.empty());
            });
  }

  private Mono<List<br.com.banco.spider.operational.readmodel.OperationalEventView>> requireVisibleExecution(
      OperationalConsoleSecurityContext ctx, String executionId) {
    return queryService
        .listOperationalEvents(executionId)
        .flatMap(
            items ->
                companyAccess.maySee(
                        ctx,
                        companyAccess.companyOfViews(items),
                        companyAccess.looksCanonical(items))
                    ? Mono.just(items)
                    : Mono.empty());
  }

  private Mono<List<OperationalExecutionListItem>> visibleItems(
      OperationalConsoleSecurityContext ctx, List<OperationalExecutionListItem> items) {
    if (!companyAccess.enabled()) {
      return Mono.just(items);
    }
    return Flux.fromIterable(items)
        .flatMap(
            item ->
                queryService
                    .listOperationalEvents(item.executionId())
                    .map(
                        events ->
                            companyAccess.maySee(
                                    ctx,
                                    companyAccess.companyOfViews(events),
                                    companyAccess.looksCanonical(events))
                                ? item
                                : null))
        .filter(Objects::nonNull)
        .collectList();
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

  private ResponseEntity<?> denied() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .cacheControl(CacheControl.noStore())
        .body(Map.of("title", "Not Found", "status", 404));
  }

  private static ResponseEntity<?> okBody(Object body) {
    return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(body);
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
