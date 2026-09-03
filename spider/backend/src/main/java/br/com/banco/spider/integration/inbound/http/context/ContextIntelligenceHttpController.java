package br.com.banco.spider.integration.inbound.http.context;

import br.com.banco.spider.application.security.AuthenticatedOriginator;
import br.com.banco.spider.application.security.CanonicalIngressAuthenticationPort;
import br.com.banco.spider.application.security.IngressAuthenticationRequest;
import br.com.banco.spider.config.ContextIntelligenceProperties;
import br.com.banco.spider.context.application.ContextDecisionRecord;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.ContextInterpretationEvidence;
import br.com.banco.spider.context.application.ContextInterpretationService;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.BusinessIntentDefinition;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.context.domain.IntentRouteResolution;
import br.com.banco.spider.execution.support.SpiderClock;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
@RequestMapping("/v1/context")
@ConditionalOnProperty(name = "spider.context.enabled", havingValue = "true")
public class ContextIntelligenceHttpController {

  private final CanonicalIngressAuthenticationPort authentication;
  private final ContextIntelligenceService context;
  private final ContextInterpretationService interpretation;
  private final ContextIntelligenceProperties properties;
  private final SpiderClock clock;

  public ContextIntelligenceHttpController(
      CanonicalIngressAuthenticationPort authentication,
      ContextIntelligenceService context,
      ContextInterpretationService interpretation,
      ContextIntelligenceProperties properties,
      SpiderClock clock) {
    this.authentication = authentication;
    this.context = context;
    this.interpretation = interpretation;
    this.properties = properties;
    this.clock = clock;
  }

  @GetMapping(value = "/intents", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> intents(
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    return authenticate(credentialRef, exchange)
        .map(
            originator -> {
              if (originator.isEmpty()) {
                return unauthorized();
              }
              List<BusinessIntentCardView> items =
                  context.catalog().list().stream().map(BusinessIntentCardView::from).toList();
              return ResponseEntity.ok()
                  .header("Cache-Control", "no-store")
                  .body(
                      new ContextCatalogView(
                          "1.0",
                          true,
                          properties.getUi().isEnabled(),
                          properties.getAi().isEnabled(),
                          interpretation.state().name(),
                          interpretation.providerId(),
                          properties.getAi().isEnabled()
                              ? "Interpretação contextual disponível."
                              : "Interpretação contextual desabilitada.",
                          items));
            });
  }

  @PostMapping(
      value = "/interpretations",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> interpret(
      @RequestBody NaturalLanguageInterpretationRequest body,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    return authenticate(credentialRef, exchange)
        .flatMap(
            originator -> {
              if (originator.isEmpty()) {
                return Mono.just(unauthorized());
              }
              return interpretation
                  .interpret(body.objective(), originator.get().principalRef())
                  .map(
                      result ->
                          ResponseEntity.ok()
                              .header("Cache-Control", "no-store")
                              .body(InterpretationView.from(result)));
            });
  }

  @PostMapping(
      value = "/intents/resolve",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> resolve(
      @RequestBody IntentContract contract,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    return authenticate(credentialRef, exchange)
        .map(
            originator -> {
              if (originator.isEmpty()) {
                return unauthorized();
              }
              ContextDecisionRecord record =
                  context.resolve(contract, originator.get().principalRef());
              return decisionResponse(record);
            });
  }

  @PostMapping(
      value = "/executions",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> execute(
      @RequestBody ContextExecutionRequest body,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    return authenticate(credentialRef, exchange)
        .flatMap(
            originator -> {
              if (originator.isEmpty()) {
                return Mono.just(unauthorized());
              }
              return context
                  .execute(body.decisionId(), body.intentContract(), originator.get())
                  .map(
                      outcome -> {
                        if (!outcome.success()) {
                          if (outcome.canonicalOutcome() != null) {
                            return ResponseEntity.status(
                                    statusFromHint(outcome.canonicalOutcome().httpHint()))
                                .header("Cache-Control", "no-store")
                                .body(
                                    Map.of(
                                        "code",
                                        outcome.canonicalOutcome().error().code(),
                                        "message",
                                        outcome.canonicalOutcome().error().message()));
                          }
                          return ResponseEntity.unprocessableEntity()
                              .header("Cache-Control", "no-store")
                              .body(
                                  Map.of(
                                      "decision",
                                      outcome.guard().decision().name(),
                                      "reasonCode",
                                      outcome.guard().reasonCode()));
                        }
                        ContextDecisionRecord record = outcome.record();
                        return ResponseEntity.ok()
                            .header("Cache-Control", "no-store")
                            .body(
                                new ContextExecutionView(
                                    record.executionId(),
                                    record.executionState(),
                                    DecisionView.from(record),
                                    outcome.canonicalOutcome().result()));
                      });
            });
  }

  @GetMapping(value = "/executions/{executionId}", produces = MediaType.APPLICATION_JSON_VALUE)
  public Mono<ResponseEntity<?>> executionContext(
      @PathVariable String executionId,
      @RequestHeader(value = "X-Spider-Credential-Ref", required = false) String credentialRef,
      ServerWebExchange exchange) {
    if (executionId == null || executionId.length() > 120) {
      return Mono.just(
          ResponseEntity.badRequest().body(Map.of("code", "INVALID_EXECUTION_ID")));
    }
    return authenticate(credentialRef, exchange)
        .map(
            originator -> {
              if (originator.isEmpty()) {
                return unauthorized();
              }
              return context
                  .findByExecutionId(executionId, originator.get().principalRef())
                  .<ResponseEntity<?>>map(
                      record ->
                          ResponseEntity.ok()
                              .header("Cache-Control", "no-store")
                              .body(DecisionView.from(record)))
                  .orElseGet(
                      () ->
                          ResponseEntity.status(HttpStatus.NOT_FOUND)
                              .body(Map.of("code", "CONTEXT_EXECUTION_NOT_FOUND")));
            });
  }

  private Mono<Optional<AuthenticatedOriginator>> authenticate(
      String credentialRef, ServerWebExchange exchange) {
    return authentication.authenticate(
        new IngressAuthenticationRequest(
            "REST_HTTP",
            credentialRef,
            Map.of(),
            exchange.getRequest().getRemoteAddress() == null
                ? null
                : exchange.getRequest().getRemoteAddress().toString(),
            clock.now()));
  }

  private static ResponseEntity<?> decisionResponse(ContextDecisionRecord record) {
    HttpStatus status =
        record.guard().accepted() ? HttpStatus.OK : statusFor(record.guard().decision());
    return ResponseEntity.status(status)
        .header("Cache-Control", "no-store")
        .body(DecisionView.from(record));
  }

  private static HttpStatus statusFor(ContextGuardDecision decision) {
    return decision == ContextGuardDecision.NOT_AUTHORIZED
        ? HttpStatus.FORBIDDEN
        : HttpStatus.UNPROCESSABLE_ENTITY;
  }

  private static HttpStatus statusFromHint(String hint) {
    try {
      return hint == null ? HttpStatus.UNPROCESSABLE_ENTITY : HttpStatus.valueOf(Integer.parseInt(hint));
    } catch (RuntimeException ignored) {
      return HttpStatus.UNPROCESSABLE_ENTITY;
    }
  }

  private static ResponseEntity<?> unauthorized() {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
        .header("Cache-Control", "no-store")
        .body(Map.of("code", "UNAUTHENTICATED"));
  }

  public record ContextCatalogView(
      String schemaVersion,
      boolean contextEnabled,
      boolean uiEnabled,
      boolean aiEnabled,
      String aiState,
      String aiProvider,
      String naturalLanguageMessage,
      List<BusinessIntentCardView> items) {}

  public record NaturalLanguageInterpretationRequest(String objective) {}

  public record InterpretationView(
      String status,
      String aiState,
      String message,
      String requestedObjective,
      DecisionView decision,
      ContextInterpretationEvidence interpretation) {
    static InterpretationView from(
        ContextInterpretationService.InterpretationResult result) {
      return new InterpretationView(
          result.status().name(),
          result.aiState().name(),
          result.message(),
          result.requestedObjective(),
          result.decision() == null ? null : DecisionView.from(result.decision()),
          result.interpretation());
    }
  }

  public record BusinessIntentCardView(
      String domain,
      String domainLabel,
      String intent,
      String title,
      String description,
      boolean demonstrative,
      IntentContract intentContract) {
    static BusinessIntentCardView from(BusinessIntentDefinition definition) {
      return new BusinessIntentCardView(
          definition.domain(),
          definition.domainLabel(),
          definition.intent(),
          definition.title(),
          definition.description(),
          true,
          definition.businessCardContract());
    }
  }

  public record PublicRouteView(
      String intent,
      String capabilityRef,
      String routeRef,
      String policyRef,
      boolean executable) {
    static PublicRouteView from(IntentRouteResolution route) {
      return route == null
          ? null
          : new PublicRouteView(
              route.intent(),
              route.capabilityRef(),
              route.routeRef(),
              route.policyRef(),
              route.executable());
    }
  }

  public record DecisionView(
      String decisionId,
      IntentContract intentContract,
      String decision,
      String reasonCode,
      String policyRef,
      PublicRouteView route,
      List<br.com.banco.spider.context.application.ContextJourneyStage> contextJourney,
      ContextInterpretationEvidence interpretation,
      String executionId,
      String executionState) {
    static DecisionView from(ContextDecisionRecord record) {
      return new DecisionView(
          record.decisionId(),
          record.intentContract(),
          record.guard().decision().name(),
          record.guard().reasonCode(),
          record.guard().policyRef(),
          PublicRouteView.from(record.route()),
          record.journey(),
          record.interpretation(),
          record.executionId(),
          record.executionState());
    }
  }

  public record ContextExecutionRequest(String decisionId, IntentContract intentContract) {}

  public record ContextExecutionView(
      String executionId,
      String state,
      DecisionView context,
      br.com.banco.spider.canonical.contract.CanonicalExecutionResult execution) {}
}
