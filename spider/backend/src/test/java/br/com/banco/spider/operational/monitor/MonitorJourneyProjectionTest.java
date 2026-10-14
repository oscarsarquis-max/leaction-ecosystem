package br.com.banco.spider.operational.monitor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MonitorJourneyProjectionTest {

  private static final String COMPANY = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";
  private static final String RUN_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  private static final String RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

  @Test
  void interactionProducesOfficialStagesWithoutInventingCanonicalPlan() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = lookupRequest("afm-direct-1", "pay-homolog-0001");
    emitFullInteraction(service, request);
    String interactionId = MonitorProjectionIds.interaction(request);
    List<String> ids = store.findStages(interactionId).stream().map(MonitorJourneyStage::stageId).toList();
    assertTrue(ids.containsAll(List.of(
            "received",
            "authenticated",
            "contract_validated",
            "company_authorized",
            "objective_accepted",
            "capability_resolved",
            "request_sent",
            "response_received",
            "result_recorded",
            "response_produced",
            "context_ai",
            "wait_signal",
            "canonical_engine")));
    assertEquals("not_used", store.findStages(interactionId).stream().filter(s -> "context_ai".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("not_used", store.findStages(interactionId).stream().filter(s -> "wait_signal".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("COMPLETED", store.findById(interactionId).orElseThrow().technicalState());
    assertTrue(store.findStages(interactionId).stream().noneMatch(stage -> "executionId".equals(stage.stageId())));
    assertEquals("COMPLETE", MonitorJourneyCatalog.availability(store.findStages(interactionId)));
  }

  @Test
  void syncPagesEnrichSameRunAndStayOrdered() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    emitSyncPage(service, listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "a1"), "pay-77", "PENDING");
    emitSyncPage(service, listRequest("list-" + RUN_A + "-2", "afp-" + RUN_A + "-2", "a2"), "pay-77", "PAID");
    String syncId = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A);
    List<String> ids = store.findStages(syncId).stream().map(MonitorJourneyStage::stageId).toList();
    assertTrue(ids.contains("sync_requested"));
    assertTrue(ids.contains("listing_capability"));
    assertTrue(ids.contains("page_1"));
    assertTrue(ids.contains("page_2"));
    assertTrue(ids.contains("payments_correlated"));
    assertTrue(ids.contains("sync_completed"));
    assertEquals("Página 1 solicitada/recebida", title(store, syncId, "page_1"));
    assertEquals("COMPLETED", store.findById(syncId).orElseThrow().technicalState());
    assertEquals(1, store.findStages(syncId).stream().filter(stage -> "page_1".equals(stage.stageId())).count());
  }

  @Test
  void twoSyncsDoNotMergeAndPaymentHasOwnJourney() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    emitSyncPage(service, listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "a1"), "pay-77", "PAID");
    emitSyncPage(service, listRequest("list-" + RUN_B + "-1", "afp-" + RUN_B + "-1", "b1"), "pay-88", "PENDING");
    String syncA = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A);
    String syncB = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_B);
    assertFalse(store.findStages(syncA).isEmpty());
    assertFalse(store.findStages(syncB).isEmpty());
    assertTrue(store.findStages(syncA).stream().noneMatch(stage -> stage.recordId().equals(syncB)));
    String payment = MonitorProjectionIds.payment(COMPANY, "pay-77");
    List<String> ids = store.findStages(payment).stream().map(MonitorJourneyStage::stageId).toList();
    assertEquals(List.of("pay_observed", "pay_discovered", "identity_correlated", "financial_state"), ids);
    assertTrue(title(store, payment, "pay_discovered").contains(RUN_A));
  }

  @Test
  void duplicateAndLateEventsDoNotDuplicateOrRegress() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "x");
    emitSyncPage(service, request, "pay-9", "PAID");
    emitSyncPage(service, request, "pay-9", "PAID");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    String syncId = MonitorProjectionIds.sync(request);
    assertEquals(1, store.findStages(syncId).stream().filter(stage -> "sync_requested".equals(stage.stageId())).count());
    assertEquals("COMPLETED", store.findById(syncId).orElseThrow().technicalState());
    assertEquals("sync_requested", store.findStages(syncId).getFirst().stageId());
    assertEquals("PAID", store.findById(MonitorProjectionIds.payment(COMPANY, "pay-9")).orElseThrow().financialState());
  }

  @Test
  void earlyRejectAfterAuthCompletesPriorStageAndLeavesRejected() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("afm-45f062cf-4076-4403-ae06-fa6cfc2e57bb", "afp-42e5b0dc-6241-41ac-b603-564de9e5a53f-1", "afm-incident");
    service.touchInteraction(request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_AUTHENTICATED, OperationalEventOutcome.SUCCESS, "actionfinance");
    service.recordReplayPassed(request);
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_CONTRACT_VALIDATED, OperationalEventOutcome.REJECTED, "INVALID_PAYLOAD");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_DECISION_CREATED, OperationalEventOutcome.REJECTED, "INVALID_PAYLOAD");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.REJECTED, "INVALID_PAYLOAD");
    String interactionId = MonitorProjectionIds.interaction(request);
    String syncId = MonitorProjectionIds.sync(request);
    List<MonitorJourneyStage> stages = store.findStages(interactionId);
    assertEquals("completed", stages.stream().filter(s -> "received".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("completed", stages.stream().filter(s -> "authenticated".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("rejected", stages.stream().filter(s -> "contract_validated".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("Validação do contrato e contexto", stages.stream().filter(s -> "contract_validated".equals(s.stageId())).findFirst().orElseThrow().title());
    assertEquals("rejected", stages.stream().filter(s -> "response_produced".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("not_reached", stages.stream().filter(s -> "capability_resolved".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("not_reached", stages.stream().filter(s -> "request_sent".equals(s.stageId())).findFirst().orElseThrow().state());
    assertEquals("not_used", stages.stream().filter(s -> "context_ai".equals(s.stageId())).findFirst().orElseThrow().state());
    assertTrue(stages.size() >= 10);
    assertEquals("REJECTED", store.findById(interactionId).orElseThrow().technicalState());
    assertEquals("REJECTED", store.findById(syncId).orElseThrow().technicalState());
    assertEquals(syncId, store.findById(interactionId).orElseThrow().relatedSyncId());
    assertEquals("COMPLETE", MonitorJourneyCatalog.availability(stages));
  }

  @Test
  void emptyListStillCompletesWithZeroCounts() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = listRequest("list-" + RUN_A + "-empty", "afp-" + RUN_A + "-1", "empty");
    service.touchInteraction(request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_AUTHENTICATED, OperationalEventOutcome.SUCCESS, "actionfinance");
    service.touchInteraction(request, OperationalEventType.OUTBOUND_REQUEST_STARTED, OperationalEventOutcome.INFO, "actionhub-pay");
    service.touchInteraction(request, OperationalEventType.PROVIDER_RESULT_RECEIVED, OperationalEventOutcome.SUCCESS, "actionhub-pay");
    service.recordDiscoveredPayments(
        request,
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-empty",
            "actionhub-pay",
            null,
            "ACTIONHUB_PAY",
            "FINANCIAL_WATERMARK",
            List.of(),
            List.of(),
            Map.of("companyId", COMPANY, "environment", "HOMOLOG", "itemCount", 0)));
    service.touchInteraction(request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
    String syncId = MonitorProjectionIds.sync(request);
    MonitorProjectionRecord sync = store.findById(syncId).orElseThrow();
    assertEquals("COMPLETED", sync.technicalState());
    assertEquals(0, n(sync.foundCount()));
    assertEquals(0, n(sync.newCount()));
    assertTrue(store.findStages(syncId).stream().anyMatch(stage -> "payments_correlated".equals(stage.stageId())));
    assertTrue(store.findStages(syncId).stream().anyMatch(stage -> "sync_completed".equals(stage.stageId())));
    assertEquals("completed", store.findStages(syncId).stream().filter(s -> "sync_requested".equals(s.stageId())).findFirst().orElseThrow().state());
  }

  @Test
  void providerUnavailableAndUnknownTimeoutAreTerminal() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest unavailable = listRequest("list-unavail-1", "afp-" + RUN_A + "-9", "unavail");
    service.touchInteraction(unavailable, OperationalEventType.OUTBOUND_REQUEST_STARTED, OperationalEventOutcome.INFO, "actionhub-pay");
    service.touchInteraction(
        unavailable, OperationalEventType.PROVIDER_RESULT_RECEIVED, OperationalEventOutcome.FAILURE, "PROVIDER_UNAVAILABLE");
    service.touchInteraction(
        unavailable, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.FAILURE, "PROVIDER_UNAVAILABLE");
    assertEquals("UNAVAILABLE", store.findById(MonitorProjectionIds.interaction(unavailable)).orElseThrow().technicalState());
    SatelliteInteractionRequest timeout = listRequest("list-timeout-1", "afp-" + RUN_B + "-9", "timeout");
    service.touchInteraction(
        timeout, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.FAILURE, "UNKNOWN_EFFECT");
    assertEquals("UNKNOWN_EFFECT", store.findById(MonitorProjectionIds.interaction(timeout)).orElseThrow().technicalState());
  }

  @Test
  void evidenceDropsSecretsAndHistoricalRecordStaysUnavailable() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    MonitorProjectionService service = new MonitorProjectionService(store);
    SatelliteInteractionRequest request = lookupRequest("afm-old", "pay-1");
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "token=secret");
    String json = store.findStages(MonitorProjectionIds.interaction(request)).getFirst().evidenceJson();
    assertFalse(json.contains("token"));
    assertFalse(json.contains("secret"));
    InMemoryMonitorProjectionStore empty = new InMemoryMonitorProjectionStore();
    empty.upsert(
        MonitorProjectionRecord.builder()
            .recordId("int:actionfinance:legacy")
            .kind(MonitorProjectionRecord.KIND_SATELLITE)
            .origin("actionfinance")
            .technicalState("RECEIVED")
            .createdAt(java.time.Instant.parse("2026-10-12T12:00:00Z"))
            .updatedAt(java.time.Instant.parse("2026-10-12T12:00:00Z"))
            .retentionUntil(java.time.Instant.parse("2026-12-12T12:00:00Z"))
            .build());
    assertEquals(MonitorJourneyStage.AVAILABILITY_UNAVAILABLE, MonitorJourneyCatalog.availability(empty.findStages("int:actionfinance:legacy")));
    assertEquals(MonitorJourneyStage.HISTORICAL_NOTICE, MonitorJourneyStage.HISTORICAL_NOTICE);
  }

  private static void emitFullInteraction(MonitorProjectionService service, SatelliteInteractionRequest request) {
    service.touchInteraction(request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_AUTHENTICATED, OperationalEventOutcome.SUCCESS, "actionfinance");
    service.recordReplayPassed(request);
    service.touchInteraction(request, OperationalEventType.SATELLITE_CONTRACT_VALIDATED, OperationalEventOutcome.SUCCESS, "VALIDATED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_CONTEXT_ACCEPTED, OperationalEventOutcome.SUCCESS, "ctx-1");
    service.touchInteraction(request, OperationalEventType.ROUTE_RESOLVED, OperationalEventOutcome.SUCCESS, "actionhub-pay");
    service.touchInteraction(request, OperationalEventType.SATELLITE_COMPANY_AUTHORIZED, OperationalEventOutcome.SUCCESS, "COMPANY_AUTHORIZED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_OBJECTIVE_ACCEPTED, OperationalEventOutcome.SUCCESS, "LOOKUP_EXTERNAL_PAYMENT");
    service.touchInteraction(request, OperationalEventType.CAPABILITY_DISPATCHED, OperationalEventOutcome.INFO, "LOOKUP_ACTIONHUB_PAYMENT");
    service.touchInteraction(request, OperationalEventType.OUTBOUND_REQUEST_STARTED, OperationalEventOutcome.INFO, "actionhub-pay");
    service.touchInteraction(request, OperationalEventType.PROVIDER_RESULT_RECEIVED, OperationalEventOutcome.SUCCESS, "actionhub-pay");
    service.touchInteraction(request, OperationalEventType.SATELLITE_DECISION_CREATED, OperationalEventOutcome.SUCCESS, "READY");
    service.touchInteraction(request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
  }

  private static void emitSyncPage(
      MonitorProjectionService service, SatelliteInteractionRequest request, String paymentId, String status) {
    service.touchInteraction(request, OperationalEventType.SATELLITE_REQUEST_RECEIVED, OperationalEventOutcome.INFO, "RECEIVED");
    service.touchInteraction(request, OperationalEventType.SATELLITE_AUTHENTICATED, OperationalEventOutcome.SUCCESS, "actionfinance");
    service.touchInteraction(request, OperationalEventType.CAPABILITY_DISPATCHED, OperationalEventOutcome.INFO, "LIST_PAYMENT_TRANSACTIONS");
    service.touchInteraction(request, OperationalEventType.OUTBOUND_REQUEST_STARTED, OperationalEventOutcome.INFO, "actionhub-pay");
    service.touchInteraction(request, OperationalEventType.PROVIDER_RESULT_RECEIVED, OperationalEventOutcome.SUCCESS, "actionhub-pay");
    service.recordDiscoveredPayments(request, listResult(paymentId, status));
    service.touchInteraction(request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
  }

  private static int n(Integer value) {
    return value == null ? 0 : value;
  }

  private static String title(InMemoryMonitorProjectionStore store, String recordId, String stageId) {
    return store.findStages(recordId).stream()
        .filter(stage -> stageId.equals(stage.stageId()))
        .map(MonitorJourneyStage::title)
        .findFirst()
        .orElse("");
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
}
