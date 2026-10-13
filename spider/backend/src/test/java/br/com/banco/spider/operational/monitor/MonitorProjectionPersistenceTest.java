package br.com.banco.spider.operational.monitor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryMonitorProjectionStore;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class MonitorProjectionPersistenceTest {

  private static final String COMPANY = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";
  private static final String RUN_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  private static final String RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

  @Test
  void listPagesShareOneSyncAndKeepDistinctInteractions() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    service.touchInteraction(
        listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "idemp-a-1"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.recordDiscoveredPayments(
        listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "idemp-a-1"),
        listResult("pay-77", "PENDING"));
    service.touchInteraction(
        listRequest("list-" + RUN_A + "-2", "afp-" + RUN_A + "-2", "idemp-a-2"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.recordDiscoveredPayments(
        listRequest("list-" + RUN_A + "-2", "afp-" + RUN_A + "-2", "idemp-a-2"),
        listResult("pay-77", "PAID"));
    String syncId = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A);
    assertEquals(syncId, MonitorProjectionIds.eventKey(listRequest("list-" + RUN_A + "-2", "afp-" + RUN_A + "-2", "x")));
    assertEquals("int:actionfinance:list-" + RUN_A + "-1", MonitorProjectionIds.interaction(listRequest("list-" + RUN_A + "-1", "c", "i")));
    assertEquals("COMPLETED", store.findById(syncId).orElseThrow().technicalState());
    assertEquals(2, store.findById(syncId).orElseThrow().pagesConsulted());
    assertEquals("PAID", store.findById(MonitorProjectionIds.payment(COMPANY, "pay-77")).orElseThrow().financialState());
    assertEquals(MonitorProjectionRecord.ORIGIN_ACTIONHUB_PAY, store.findById(MonitorProjectionIds.payment(COMPANY, "pay-77")).orElseThrow().origin());
    assertTrue(store.findById("int:actionfinance:list-" + RUN_A + "-1").isPresent());
    assertTrue(store.findById("int:actionfinance:list-" + RUN_A + "-2").isPresent());
  }

  @Test
  void twoSyncRunsStayDistinctAndDoNotCollapseByCompany() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    service.touchInteraction(
        listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "a"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.touchInteraction(
        listRequest("list-" + RUN_B + "-1", "afp-" + RUN_B + "-1", "b"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    assertNotEquals(
        MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A),
        MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_B));
    assertTrue(store.findById(MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A)).isPresent());
    assertTrue(store.findById(MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_B)).isPresent());
    assertTrue(store.findById("int:actionfinance:list:" + COMPANY + ":HOMOLOG").isEmpty());
  }

  @Test
  void delayedEventDoesNotRegressReadyOrPaid() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "x");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    service.recordDiscoveredPayments(request, listResult("pay-9", "PAID"));
    service.recordDiscoveredPayments(request, listResult("pay-9", "PENDING"));
    assertEquals("COMPLETED", store.findById(MonitorProjectionIds.sync(request)).orElseThrow().technicalState());
    assertEquals("PAID", store.findById(MonitorProjectionIds.payment(COMPANY, "pay-9")).orElseThrow().financialState());
  }

  @Test
  void directLookupKeepsMessageIdentityAndLinksPayment() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest lookup = lookupRequest("afm-direct-1", "pay-homolog-0001");
    service.touchInteraction(
        lookup, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
    service.recordDiscoveredPayments(lookup, listResult("pay-homolog-0001", "CONFIRMED"));
    assertEquals("int:actionfinance:afm-direct-1", MonitorProjectionIds.interaction(lookup));
    assertNull(MonitorProjectionIds.sync(lookup));
    assertEquals("int:actionfinance:afm-direct-1", store.findById("int:actionfinance:afm-direct-1").orElseThrow().recordId());
    assertEquals(
        "int:actionfinance:afm-direct-1",
        store.findById(MonitorProjectionIds.payment(COMPANY, "pay-homolog-0001")).orElseThrow().relatedInteractionId());
    assertNull(store.findById("int:actionfinance:afm-direct-1").orElseThrow().executionId());
  }

  @Test
  void searchFindsPaymentAfterLeavingRecentWindow() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "old");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
    service.recordDiscoveredPayments(request, listResult("txn-hidden", "AUTHORIZED"));
    String paymentId = MonitorProjectionIds.payment(COMPANY, "txn-hidden");
    for (int i = 0; i < 6; i++) {
      service.touchInteraction(
          segsenseRequest("sat-" + i),
          OperationalEventType.SATELLITE_RESPONSE_RETURNED,
          OperationalEventOutcome.SUCCESS,
          "READY");
    }
    List<MonitorProjectionRecord> recent = store.search("", null, null, Instant.now(), 5, null, null);
    assertEquals(5, recent.size());
    List<MonitorProjectionRecord> byPay = store.search("txn-hidden", "actionhub-pay", null, Instant.now(), 10, null, null);
    assertEquals(1, byPay.size());
    assertEquals(MonitorProjectionRecord.KIND_PAYMENT, byPay.getFirst().kind());
    assertNull(byPay.getFirst().executionId());
    assertTrue(store.findById(paymentId).isPresent());
  }

  @Test
  void concurrentUpsertsKeepPaidAndSinglePayment() throws Exception {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "c");
    CountDownLatch start = new CountDownLatch(1);
    try (var pool = Executors.newFixedThreadPool(8)) {
      for (int i = 0; i < 8; i++) {
        String status = i % 2 == 0 ? "PENDING" : "PAID";
        pool.submit(
            () -> {
              start.await();
              service.recordDiscoveredPayments(request, listResult("pay-race", status));
              return null;
            });
      }
      start.countDown();
      pool.shutdown();
      assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
    }
    assertEquals("PAID", store.findById(MonitorProjectionIds.payment(COMPANY, "pay-race")).orElseThrow().financialState());
    assertEquals(1, store.search("pay-race", null, MonitorProjectionRecord.KIND_PAYMENT, Instant.now(), 10, null, null).size());
  }

  @Test
  void retentionPurgeUsesClockAndKeepsLiveRecords() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    Instant start = Instant.parse("2026-07-01T00:00:00Z");
    MonitorProjectionService service =
        new MonitorProjectionService(store, Duration.ofDays(90), Clock.fixed(start, ZoneOffset.UTC));
    service.touchInteraction(
        segsenseRequest("old-1"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    assertEquals(0, service.purgeExpired());
    MonitorProjectionService later =
        new MonitorProjectionService(
            store, Duration.ofDays(90), Clock.fixed(start.plus(Duration.ofDays(91)), ZoneOffset.UTC));
    assertEquals(1, later.purgeExpired());
    assertTrue(store.findById("int:segsense:old-1").isEmpty());
  }

  @Test
  void memoryAdapterIsExplicitlyVolatile() {
    assertEquals(false, new InMemoryMonitorProjectionStore().isDurable());
  }

  @Test
  void invalidMonitorModeFailsFast() {
    org.junit.jupiter.api.Assertions.assertThrows(
        IllegalStateException.class, () -> new br.com.banco.spider.config.MonitorProjectionConfig("redis"));
  }

  private static ExecutionResult listResult(String transactionId, String status) {
    return new ExecutionResult(
        true,
        "COMPLETED",
        "preq-1",
        "actionhub-pay",
        "pref-1",
        "ACTIONHUB_PAY",
        "FINANCIAL_WATERMARK",
        List.of(),
        List.of(),
        Map.of(
            "companyId",
            COMPANY,
            "environment",
            "HOMOLOG",
            "items",
            List.of(Map.of("transactionId", transactionId, "normalizedStatus", status, "originalStatus", status))));
  }

  private static SatelliteInteractionRequest listRequest(String messageId, String correlationId, String idempotency) {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.4",
        messageId,
        correlationId,
        "actionfinance",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        idempotency,
        "FINANCIAL_EXTERNAL_LIST",
        new Objective("LIST_EXTERNAL_PAYMENTS", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.4",
                "INTERNAL",
                true,
                new Provenance("SATELLITE_GOVERNED", "ACTIONFINANCE_FINANCIAL_LIST_V1", now, "SERVER_REGISTRY", "GOVERNED"),
                Map.of("channel", "ACTIONFINANCE_HOMOLOG", "companyId", COMPANY),
                List.of(),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of("financialList", Map.of("companyId", COMPANY, "environment", "HOMOLOG", "originSystem", "ACTIONHUB_PAY")));
  }

  private static SatelliteInteractionRequest lookupRequest(String messageId, String reference) {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.3",
        messageId,
        "afc-" + messageId,
        "actionfinance",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "lookup:" + COMPANY + ":" + reference,
        "FINANCIAL_EXTERNAL_LOOKUP",
        new Objective("LOOKUP_EXTERNAL_PAYMENT", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.3",
                "INTERNAL",
                true,
                new Provenance("SATELLITE_GOVERNED", "ACTIONFINANCE_FINANCIAL_LOOKUP_V1", now, "SERVER_REGISTRY", "GOVERNED"),
                Map.of("channel", "ACTIONFINANCE_HOMOLOG", "companyId", COMPANY),
                List.of(),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of("financialLookup", Map.of("companyId", COMPANY, "externalReference", reference, "originSystem", "ACTIONHUB_PAY")));
  }

  private static SatelliteInteractionRequest segsenseRequest(String messageId) {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.5",
        messageId,
        "corr-" + messageId,
        "segsense",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "idemp-" + messageId,
        "UNDERSTAND_FAMILY_PROTECTION_OPTIONS",
        new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", now),
        new ContextBlock(null, null),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of());
  }
}
