package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class DeterministicRouteResolver implements RouteResolverPort {

  private static final Logger log = LoggerFactory.getLogger(DeterministicRouteResolver.class);

  private final RouteCatalogPort catalog;
  private final RouteDefinitionValidator validator;

  public DeterministicRouteResolver(RouteCatalogPort catalog, RouteDefinitionValidator validator) {
    this.catalog = catalog;
    this.validator = validator;
  }

  @Override
  public Mono<RouteResolution> resolve(CanonicalExecutionRequest request) {
    String journeyRef = request.contextRef().journeyId();
    String capability = request.target().capability();
    String operation = request.target().operation();

    return catalog
        .findPublishedCandidates(journeyRef, capability, operation)
        .map(candidates -> select(candidates, capability, operation));
  }

  private RouteResolution select(
      List<RouteDefinition> candidates, String capability, String operation) {
    List<String> codes = candidates.stream().map(r -> r.routeCode() + "@" + r.version()).toList();

    if (candidates.isEmpty()) {
      log.info(
          "event=route_rejected reasonCode={} capability={} operation={}",
          RouteResolutionReasonCode.ROUTE_NOT_FOUND,
          capability,
          operation);
      return RouteResolution.rejected(
          RouteResolutionReasonCode.ROUTE_NOT_FOUND,
          codes,
          List.of(
              error(
                  "ROUTE_NOT_FOUND",
                  "No published route for journey/capability/operation",
                  ErrorCategory.RESOLUTION)),
          "no candidates");
    }

    List<RouteDefinition> valid = new ArrayList<>();
    List<CanonicalError> invalidErrors = new ArrayList<>();
    for (RouteDefinition candidate : candidates) {
      if (!candidate.target().capabilityCode().equals(capability)
          || !candidate.target().operationCode().equals(operation)) {
        invalidErrors.add(
            error("ROUTE_TARGET_MISMATCH", "Candidate target mismatch", ErrorCategory.RESOLUTION));
        continue;
      }
      List<CanonicalError> errs = validator.validateForSelection(candidate);
      if (!errs.isEmpty()) {
        invalidErrors.addAll(errs);
        continue;
      }
      valid.add(candidate);
    }

    if (valid.isEmpty()) {
      RouteResolutionReasonCode reason =
          invalidErrors.stream().anyMatch(e -> "ROUTE_TARGET_MISMATCH".equals(e.code()))
              ? RouteResolutionReasonCode.ROUTE_TARGET_MISMATCH
              : RouteResolutionReasonCode.ROUTE_INVALID;
      log.info("event=route_rejected reasonCode={} candidates={}", reason, codes.size());
      return RouteResolution.rejected(reason, codes, invalidErrors, "no valid candidates");
    }

    int maxPriority = valid.stream().mapToInt(RouteDefinition::priority).max().orElse(Integer.MIN_VALUE);
    List<RouteDefinition> top =
        valid.stream().filter(r -> r.priority() == maxPriority).toList();

    if (top.size() > 1) {
      log.info(
          "event=route_rejected reasonCode={} topPriority={} tied={}",
          RouteResolutionReasonCode.ROUTE_AMBIGUOUS,
          maxPriority,
          top.size());
      return RouteResolution.rejected(
          RouteResolutionReasonCode.ROUTE_AMBIGUOUS,
          codes,
          List.of(
              error(
                  "ROUTE_AMBIGUOUS",
                  "Multiple published routes share the highest priority=" + maxPriority,
                  ErrorCategory.RESOLUTION)),
          "tie at priority " + maxPriority);
    }

    RouteDefinition winner = top.getFirst();
    // Ordenação por prioridade explícita apenas; sem desempate por inserção.
    List<RouteDefinition> ordered =
        valid.stream()
            .sorted(Comparator.comparingInt(RouteDefinition::priority).reversed())
            .toList();
    log.info(
        "event=route_selected reasonCode={} routeCode={} routeVersion={} priority={} orderedCount={}",
        RouteResolutionReasonCode.ROUTE_SELECTED,
        winner.routeCode(),
        winner.version(),
        winner.priority(),
        ordered.size());
    return RouteResolution.selected(winner, codes);
  }

  private static CanonicalError error(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + java.util.UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(java.time.Instant.now())
        .source(new CanonicalError.ErrorSource("route_resolver", null, null, null))
        .build();
  }
}
