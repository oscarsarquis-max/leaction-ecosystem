package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.application.security.LocalDemoCanonicalCredentials;
import br.com.banco.spider.context.application.ContextDecisionRecord;
import br.com.banco.spider.context.application.ContextDecisionStore;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.ContextInterpretationService;
import br.com.banco.spider.context.application.ContextInterpretationService.InterpretationResult;
import br.com.banco.spider.context.application.ContextInterpretationService.InterpretationStatus;
import br.com.banco.spider.context.application.PageContextFacts;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.CropFailurePolicy;
import br.com.banco.spider.contextuallink.domain.ContextAcquisitionStatus;
import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import br.com.banco.spider.contextuallink.domain.PageContext;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Mono;

/**
 * Orquestra objetivo declarado + PageContext permitido no Context Intelligence existente.
 *
 * <p>Não cria Intent a partir do link. Não executa o Data Plane.
 */
public final class SpiderBankUnderstandService {

  public static final String SOURCE = "spiderbank-understand";

  private final ContextualLinkGatewayService gateway;
  private final ContextInterpretationService interpretation;
  private final ContextIntelligenceService intelligence;
  private final ContextDecisionStore decisions;
  private final OperationalEventPublisher events;

  public SpiderBankUnderstandService(
      ContextualLinkGatewayService gateway,
      ContextInterpretationService interpretation,
      ContextIntelligenceService intelligence,
      ContextDecisionStore decisions,
      OperationalEventPublisher events) {
    this.gateway = gateway;
    this.interpretation = interpretation;
    this.intelligence = intelligence;
    this.decisions = decisions;
    this.events = events;
  }

  public Mono<Map<String, Object>> understand(UnderstandCommand command) {
    if (command == null || blank(command.objective()) && blank(command.amount())) {
      return Mono.error(
          new ResponseStatusException(HttpStatus.BAD_REQUEST, "objective or amount required"));
    }
    if (!blank(command.amount()) && !blank(command.decisionId())) {
      return Mono.fromCallable(() -> continueWithAmount(command));
    }
    if (blank(command.objective())) {
      return Mono.error(new ResponseStatusException(HttpStatus.BAD_REQUEST, "objective required"));
    }
    return interpretFresh(command);
  }

  private Mono<Map<String, Object>> interpretFresh(UnderstandCommand command) {
    ContextualLinkSession session = sessionOf(command.contextId());
    PageContextFacts facts = factsFrom(session);
    boolean directEntry = session == null;
    String correlation = correlationId(session, null);
    publish(
        OperationalEventType.OBJECTIVE_DECLARED,
        correlation,
        correlation,
        OperationalEventOutcome.INFO,
        "OBJECTIVE_DECLARED",
        Map.of(
            "directEntry",
            Boolean.toString(directEntry),
            "pageUsed",
            Boolean.toString(facts.present())));
    return interpretation
        .interpret(command.objective(), LocalDemoCanonicalCredentials.CREDENTIAL_REF, facts)
        .map(result -> projectAfterInterpret(command.objective(), session, facts, directEntry, result));
  }

  private Map<String, Object> continueWithAmount(UnderstandCommand command) {
    ContextDecisionRecord previous =
        decisions
            .findByDecisionId(command.decisionId())
            .orElseThrow(
                () -> new ResponseStatusException(HttpStatus.NOT_FOUND, "unknown decision"));
    String amount = DemoAmountParser.parse(command.amount());
    if (amount == null) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "amount required");
    }
    Map<String, String> entities = new LinkedHashMap<>(previous.intentContract().entities());
    if (entities.containsKey("amount") && !amount.equals(entities.get("amount"))) {
      // o valor informado pelo cliente substitui; nunca inventamos 80000
    }
    entities.put("amount", amount);
    IntentContract next = previous.intentContract().withEntities(entities);
    ContextDecisionRecord decision =
        intelligence.resolve(
            next, LocalDemoCanonicalCredentials.CREDENTIAL_REF, previous.interpretation());
    ContextualLinkSession session = sessionOf(command.contextId());
    attach(session, decision);
    String objective =
        previous.interpretation() == null
            ? command.objective()
            : previous.interpretation().requestedObjective();
    PageContextFacts facts = factsFrom(session);
    return SpiderBankUnderstandProjector.project(
        "UNDERSTOOD",
        objective,
        session,
        facts,
        session == null,
        decision,
        CropFailurePolicy.sources(objective, facts.title(), facts.excerpt()),
        amount,
        "USER_PROVIDED",
        false);
  }

  private Map<String, Object> projectAfterInterpret(
      String objective,
      ContextualLinkSession session,
      PageContextFacts facts,
      boolean directEntry,
      InterpretationResult result) {
    ContextDecisionRecord decision = result.decision();
    attach(session, decision);
    List<String> cropSources =
        CropFailurePolicy.sources(objective, facts.title(), facts.excerpt());
    if (cropSources.contains(CropFailurePolicy.PAGE_CONTEXT)) {
      String correlation = correlationId(session, decision);
      publish(
          OperationalEventType.CONTEXT_ENRICHMENT_APPLIED,
          correlation,
          correlation,
          OperationalEventOutcome.SUCCESS,
          "PAGE_CONTEXT",
          Map.of(
              "entity",
              CropFailurePolicy.ENTITY,
              "value",
              CropFailurePolicy.CROP_FAILURE,
              "source",
              CropFailurePolicy.PAGE_CONTEXT));
    }
    String status = overlayStatus(result, decision);
    String amount =
        decision == null ? null : decision.intentContract().entities().get("amount");
    return SpiderBankUnderstandProjector.project(
        status,
        result.requestedObjective() == null ? objective : result.requestedObjective(),
        session,
        facts,
        directEntry,
        decision,
        cropSources,
        amount,
        amount == null ? null : "OBJECTIVE_TEXT",
        false);
  }

  private static String overlayStatus(
      InterpretationResult result, ContextDecisionRecord decision) {
    return switch (result.status()) {
      case AMBIGUOUS -> "AMBIGUOUS";
      case UNSUPPORTED_INTENT, REJECTED -> "UNSUPPORTED";
      case DISABLED, PROVIDER_UNAVAILABLE, TIMEOUT, INVALID_RESPONSE, INVALID_INPUT -> "FAILED";
      case MISSING_CONTEXT -> "NEED_MORE";
      case SUCCEEDED ->
          decision != null
                  && "SEEK_WORKING_CAPITAL".equals(decision.intentContract().intent())
                  && blank(decision.intentContract().entities().get("amount"))
              ? "NEED_AMOUNT"
              : "UNDERSTOOD";
    };
  }

  private ContextualLinkSession sessionOf(String contextId) {
    if (blank(contextId)) {
      return null;
    }
    if (!contextId.startsWith("ctx-")) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "opaque context required");
    }
    return gateway
        .find(contextId)
        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "unknown context"));
  }

  private void attach(ContextualLinkSession session, ContextDecisionRecord decision) {
    if (session == null || decision == null) {
      return;
    }
    String planId = decision.executionPlan() == null ? null : decision.executionPlan().planId();
    gateway.attachDecision(session.click().contextId(), decision.decisionId(), planId);
  }

  private PageContextFacts factsFrom(ContextualLinkSession session) {
    if (session == null) {
      return PageContextFacts.none();
    }
    PageContext page = session.page();
    if (page.acquisitionStatus() != ContextAcquisitionStatus.CAPTURED) {
      return PageContextFacts.none();
    }
    return new PageContextFacts(page.sourceTitle(), page.safeExtractedText());
  }

  private static String correlationId(
      ContextualLinkSession session, ContextDecisionRecord decision) {
    if (session != null) {
      return session.click().clickId();
    }
    return decision == null ? "direct-entry" : decision.decisionId();
  }

  private void publish(
      OperationalEventType type,
      String executionId,
      String correlationId,
      OperationalEventOutcome outcome,
      String reason,
      Map<String, String> extra) {
    OperationalEventAttributes.Builder attributes =
        OperationalEventAttributes.builder().component(SOURCE).reasonCode(reason);
    extra.forEach(attributes::put);
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(type, executionId, correlationId, SOURCE, outcome, null, attributes.build()));
  }

  private static boolean blank(String value) {
    return value == null || value.isBlank();
  }

  public record UnderstandCommand(String contextId, String objective, String amount, String decisionId) {}
}
