package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.config.ContextualLinkProperties;
import br.com.banco.spider.contextuallink.domain.BoundaryFlags;
import br.com.banco.spider.contextuallink.domain.ClickContext;
import br.com.banco.spider.contextuallink.domain.ContentFingerprint;
import br.com.banco.spider.contextuallink.domain.ContextAcquisitionStatus;
import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import br.com.banco.spider.contextuallink.domain.CorrelationChain;
import br.com.banco.spider.contextuallink.domain.HtmlExcerptExtractor;
import br.com.banco.spider.contextuallink.domain.PageContext;
import br.com.banco.spider.contextuallink.domain.ProvenanceStep;
import br.com.banco.spider.contextuallink.domain.ReferrerAvailability;
import br.com.banco.spider.contextuallink.domain.ReferrerClassifier;
import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard;
import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard.BlockedAcquisitionException;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import reactor.core.publisher.Mono;

public final class ContextualLinkGatewayService {

  public static final String SOURCE = "contextual-link-gateway";

  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final ContextualLinkStore store;
  private final PageAcquisitionPort pages;
  private final AcquisitionUrlGuard guard;
  private final OperationalEventPublisher events;
  private final ContextualLinkProperties properties;

  public ContextualLinkGatewayService(
      IdentifierGenerator ids,
      SpiderClock clock,
      ContextualLinkStore store,
      PageAcquisitionPort pages,
      AcquisitionUrlGuard guard,
      OperationalEventPublisher events,
      ContextualLinkProperties properties) {
    this.ids = ids;
    this.clock = clock;
    this.store = store;
    this.pages = pages;
    this.guard = guard;
    this.events = events;
    this.properties = properties;
  }

  public Mono<ContextualLinkSession> handleClick(String refererHeader) {
    Instant clickedAt = clock.now();
    String clickId = ids.nextId("clk");
    String contextId = ids.nextId("ctx");
    var classified = ReferrerClassifier.classify(refererHeader);
    String gatewayUrl = properties.gatewayPublicUrl();

    emit(clickId, contextId, OperationalEventType.CONTEXTUAL_LINK_CLICKED, OperationalEventOutcome.INFO, classified.availability().name());
    emit(clickId, contextId, OperationalEventType.CLICK_CONTEXT_CREATED, OperationalEventOutcome.SUCCESS, classified.availability().name());

    List<ProvenanceStep> steps = new ArrayList<>();
    steps.add(step(1, "LINK_CLICKED", "Link clicado", clickedAt, "OK", gatewayUrl));
    steps.add(step(2, "CLICK_ID_CREATED", "Click ID criado", clock.now(), "OK", clickId));
    steps.add(
        step(
            3,
            "REFERRER_RECEIVED",
            "Referer recebido",
            clock.now(),
            classified.availability().name(),
            classified.referrer().isBlank() ? "ausente — Referer não é garantido no mundo real" : classified.referrer()));

    Mono<PageContext> pageMono =
        switch (classified.availability()) {
          case FULL_REFERRER_AVAILABLE -> acquire(clickId, contextId, classified.fullUri(), steps);
          case ORIGIN_ONLY -> {
            Instant at = clock.now();
            steps.add(
                step(
                    4,
                    "PAGE_ACQUIRED",
                    "Página adquirida",
                    at,
                    ContextAcquisitionStatus.ORIGIN_ONLY.name(),
                    "Apenas origem disponível; a reportagem não foi inventada"));
            steps.add(step(5, "FINGERPRINT_CALCULATED", "Fingerprint calculado", at, "SKIPPED", "sem conteúdo de página"));
            yield Mono.just(
                new PageContext(
                    contextId,
                    clickId,
                    "",
                    "",
                    classified.origin(),
                    "",
                    at,
                    ContextAcquisitionStatus.ORIGIN_ONLY,
                    ""));
          }
          case REFERRER_UNAVAILABLE -> {
            Instant at = clock.now();
            steps.add(
                step(
                    4,
                    "PAGE_ACQUIRED",
                    "Página adquirida",
                    at,
                    ContextAcquisitionStatus.UNAVAILABLE.name(),
                    "Contexto de origem não pôde ser adquirido"));
            steps.add(step(5, "FINGERPRINT_CALCULATED", "Fingerprint calculado", at, "SKIPPED", "sem Referer"));
            yield Mono.just(PageContext.unavailable(contextId, clickId, at, ContextAcquisitionStatus.UNAVAILABLE));
          }
        };

    return pageMono.map(
        page -> {
          Instant done = clock.now();
          steps.add(step(6, "CONTEXT_ID_CREATED", "Context ID criado", done, "OK", contextId));
          URI redirect = URI.create(properties.spiderbankEntryUrl() + "?ctx=" + contextId);
          steps.add(step(7, "REDIRECT_CREATED", "Redirect realizado", done, "OK", redirect.toString()));
          emit(
              clickId,
              contextId,
              OperationalEventType.SPIDERBANK_REDIRECT_CREATED,
              OperationalEventOutcome.SUCCESS,
              "302");

          ClickContext click =
              new ClickContext(
                  clickId,
                  clickedAt,
                  ClickContext.SOURCE_TYPE,
                  classified.referrer(),
                  classified.origin(),
                  classified.availability(),
                  page.acquisitionStatus(),
                  contextId);
          ContextualLinkSession session =
              new ContextualLinkSession(
                  click,
                  page,
                  CorrelationChain.of(clickId, contextId),
                  BoundaryFlags.demo001(),
                  steps,
                  gatewayUrl,
                  redirect,
                  done);
          store.save(session);
          return session;
        });
  }

  public Optional<ContextualLinkSession> find(String contextId) {
    return store.findByContextId(contextId);
  }

  public Optional<ContextualLinkSession> attachDecision(
      String contextId, String decisionId, String planId) {
    return find(contextId)
        .map(
            session -> {
              boolean planCreated = planId != null && !planId.isBlank();
              ContextualLinkSession updated =
                  session.withCorrelation(
                      session.correlation().withDecision(decisionId, planId),
                      session.boundary().afterUnderstand(planCreated));
              store.save(updated);
              return updated;
            });
  }

  private Mono<PageContext> acquire(
      String clickId, String contextId, URI referrer, List<ProvenanceStep> steps) {
    Instant started = clock.now();
    emit(
        clickId,
        contextId,
        OperationalEventType.PAGE_CONTEXT_ACQUISITION_STARTED,
        OperationalEventOutcome.INFO,
        "STARTED");
    URI allowed;
    try {
      allowed = guard.validate(referrer.toString());
    } catch (BlockedAcquisitionException ex) {
      steps.add(
          step(
              4,
              "PAGE_ACQUIRED",
              "Página adquirida",
              started,
              ContextAcquisitionStatus.BLOCKED.name(),
              "Aquisição bloqueada: " + ex.getMessage()));
      steps.add(step(5, "FINGERPRINT_CALCULATED", "Fingerprint calculado", started, "SKIPPED", "origem não permitida"));
      emit(
          clickId,
          contextId,
          OperationalEventType.PAGE_CONTEXT_ACQUISITION_FAILED,
          OperationalEventOutcome.REJECTED,
          ex.getMessage());
      return Mono.just(
          new PageContext(
              contextId,
              clickId,
              referrer.toString(),
              "",
              ReferrerClassifier.originOf(referrer),
              "",
              started,
              ContextAcquisitionStatus.BLOCKED,
              ""));
    }

    return pages
        .fetch(allowed)
        .map(
            fetched -> {
              Instant at = clock.now();
              var excerpt = HtmlExcerptExtractor.extract(fetched.body());
              String fingerprint =
                  ContentFingerprint.sha256(
                      fetched.finalUri().toString(),
                      excerpt.title(),
                      excerpt.description(),
                      excerpt.text());
              steps.add(
                  step(
                      4,
                      "PAGE_ACQUIRED",
                      "Página adquirida",
                      at,
                      ContextAcquisitionStatus.CAPTURED.name(),
                      fetched.finalUri().toString()));
              steps.add(step(5, "FINGERPRINT_CALCULATED", "Fingerprint calculado", at, "OK", fingerprint));
              emit(
                  clickId,
                  contextId,
                  OperationalEventType.PAGE_CONTEXT_ACQUIRED,
                  OperationalEventOutcome.SUCCESS,
                  "CAPTURED");
              return new PageContext(
                  contextId,
                  clickId,
                  fetched.finalUri().toString(),
                  excerpt.title(),
                  ReferrerClassifier.originOf(fetched.finalUri()),
                  fingerprint,
                  at,
                  ContextAcquisitionStatus.CAPTURED,
                  excerpt.text());
            })
        .onErrorResume(
            error -> {
              Instant at = clock.now();
              String reason =
                  error instanceof BlockedAcquisitionException
                      ? error.getMessage()
                      : error.getClass().getSimpleName();
              ContextAcquisitionStatus status =
                  error instanceof BlockedAcquisitionException
                      ? ContextAcquisitionStatus.BLOCKED
                      : ContextAcquisitionStatus.FAILED;
              steps.add(
                  step(
                      4,
                      "PAGE_ACQUIRED",
                      "Página adquirida",
                      at,
                      status.name(),
                      "Falha na aquisição: " + reason));
              steps.add(step(5, "FINGERPRINT_CALCULATED", "Fingerprint calculado", at, "SKIPPED", reason));
              emit(
                  clickId,
                  contextId,
                  OperationalEventType.PAGE_CONTEXT_ACQUISITION_FAILED,
                  OperationalEventOutcome.FAILURE,
                  reason);
              return Mono.just(
                  new PageContext(
                      contextId,
                      clickId,
                      allowed.toString(),
                      "",
                      ReferrerClassifier.originOf(allowed),
                      "",
                      at,
                      status,
                      ""));
            });
  }

  private ProvenanceStep step(
      int order, String code, String label, Instant at, String status, String detail) {
    return new ProvenanceStep(order, code, label, at, status, detail);
  }

  private void emit(
      String clickId,
      String contextId,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String reason) {
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            clickId,
            contextId,
            SOURCE,
            outcome,
            null,
            OperationalEventAttributes.builder()
                .component(SOURCE)
                .reasonCode(reason)
                .put("provenance", "CONTEXTUAL_LINK")
                .technicalStatus(type.name())
                .build()));
  }
}
