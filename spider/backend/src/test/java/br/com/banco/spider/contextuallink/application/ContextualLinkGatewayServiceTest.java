package br.com.banco.spider.contextuallink.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.ContextualLinkProperties;
import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard;
import br.com.banco.spider.contextuallink.domain.ContextAcquisitionStatus;
import br.com.banco.spider.contextuallink.domain.ReferrerAvailability;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.operational.events.SafeOperationalEventPublisher;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import java.net.URI;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class ContextualLinkGatewayServiceTest {

  private final Instant now = Instant.parse("2026-09-09T14:00:00Z");
  private final List<OperationalEvent> stored = new CopyOnWriteArrayList<>();
  private ContextualLinkGatewayService service;
  private InMemoryContextualLinkStore store;

  @BeforeEach
  void setUp() {
    stored.clear();
    store = new InMemoryContextualLinkStore();
    ContextualLinkProperties properties = new ContextualLinkProperties();
    properties.setEnabled(true);
    properties.setPublicBaseUrl("http://127.0.0.1:8080");
    properties.setSpiderbankEntryUrl("http://127.0.0.1:5180/spiderbank");
    properties.getAcquisition().setAllowedOrigins(List.of("http://127.0.0.1:5180"));
    properties.getAcquisition().setAllowedPathPrefixes(List.of("/partner/"));
    AcquisitionUrlGuard guard =
        new AcquisitionUrlGuard(
            properties.getAcquisition().getAllowedOrigins(),
            properties.getAcquisition().getAllowedPathPrefixes());
    PageAcquisitionPort pages =
        uri ->
            Mono.just(
                new PageAcquisitionPort.FetchedPage(
                    uri,
                    """
                    <html><head><title>Quebra de safra pressiona produtores</title>
                    <meta name="description" content="Demo"></head>
                    <body><article><p>Texto editorial relevante da reportagem.</p></article></body></html>
                    """));
    OperationalEventPublisher events =
        new SafeOperationalEventPublisher(
            IdentifierGenerator.sequential("ev"),
            SpiderClock.fixed(now),
            new OperationalEventStorePort() {
              @Override
              public void append(OperationalEvent event) {
                stored.add(event);
              }

              @Override
              public List<OperationalEvent> findByExecutionId(String executionId) {
                return stored.stream().filter(event -> executionId.equals(event.executionId())).toList();
              }
            },
            new OperationalRedactionService());
    service =
        new ContextualLinkGatewayService(
            IdentifierGenerator.sequential("demo"),
            SpiderClock.fixed(now),
            store,
            pages,
            guard,
            events,
            properties);
  }

  @Test
  void fullReferrerCreatesIdsTimestampFingerprintAndRedirect() {
    var session =
        service.handleClick("http://127.0.0.1:5180/partner/agro-hoje/").block();
    assertTrue(session.click().clickId().startsWith("clk-"));
    assertTrue(session.click().contextId().startsWith("ctx-"));
    assertEquals(now, session.click().createdAt());
    assertEquals(ReferrerAvailability.FULL_REFERRER_AVAILABLE, session.click().referrerAvailability());
    assertEquals(ContextAcquisitionStatus.CAPTURED, session.page().acquisitionStatus());
    assertTrue(session.page().contentFingerprint().startsWith("sha256:"));
    assertEquals("Quebra de safra pressiona produtores", session.page().sourceTitle());
    assertTrue(session.redirectTo().toString().contains("ctx=" + session.click().contextId()));
    assertTrue(session.redirectTo().toString().startsWith("http://127.0.0.1:5180/spiderbank?ctx="));
    assertFalse(session.redirectTo().toString().contains("/console"));
    assertFalse(session.redirectTo().toString().contains("quebra"));
    assertFalse(session.boundary().intentCreated());
    assertFalse(session.boundary().executionPlanCreated());
    assertFalse(session.boundary().dataPlaneStarted());
    assertEquals(session.click().clickId(), session.correlation().clickId());
    assertEquals(session.click().contextId(), session.correlation().contextId());
    assertEquals(null, session.correlation().decisionId());
    assertEquals(null, session.correlation().planId());
    assertEquals(null, session.correlation().executionId());
    assertTrue(
        stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.CONTEXTUAL_LINK_CLICKED));
    assertTrue(
        stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.CLICK_CONTEXT_CREATED));
    assertTrue(
        stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.PAGE_CONTEXT_ACQUIRED));
    assertTrue(
        stored.stream()
            .anyMatch(event -> event.eventType() == OperationalEventType.SPIDERBANK_REDIRECT_CREATED));
    assertFalse(stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.INTENT_CREATED));
    assertFalse(
        stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.EXECUTION_PLAN_RESOLVED));
    assertFalse(
        stored.stream().anyMatch(event -> event.eventType() == OperationalEventType.EXECUTION_STARTED));
  }

  @Test
  void originOnlyDoesNotInventPage() {
    var session = service.handleClick("http://127.0.0.1:5180/").block();
    assertEquals(ReferrerAvailability.ORIGIN_ONLY, session.click().referrerAvailability());
    assertEquals(ContextAcquisitionStatus.ORIGIN_ONLY, session.page().acquisitionStatus());
    assertEquals("", session.page().sourceTitle());
    assertEquals("", session.page().contentFingerprint());
    assertEquals("http://127.0.0.1:5180", session.page().sourceOrigin());
  }

  @Test
  void missingReferrerCreatesMinimalContext() {
    var session = service.handleClick(null).block();
    assertEquals(ReferrerAvailability.REFERRER_UNAVAILABLE, session.click().referrerAvailability());
    assertEquals(ContextAcquisitionStatus.UNAVAILABLE, session.page().acquisitionStatus());
    assertEquals("", session.page().sourceUrl());
    assertTrue(session.click().contextId().startsWith("ctx-"));
    assertTrue(
        stored.stream()
            .noneMatch(event -> event.eventType() == OperationalEventType.PAGE_CONTEXT_ACQUIRED));
  }

  @Test
  void blockedPathDoesNotFetchArbitraryLocalhost() {
    var session = service.handleClick("http://127.0.0.1:5180/actuator/health").block();
    assertEquals(ContextAcquisitionStatus.BLOCKED, session.page().acquisitionStatus());
    assertTrue(
        stored.stream()
            .anyMatch(event -> event.eventType() == OperationalEventType.PAGE_CONTEXT_ACQUISITION_FAILED));
  }
}
