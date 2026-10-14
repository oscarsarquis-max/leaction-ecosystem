package br.com.banco.spider.operational.monitor;

import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.DemoSliceRules;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class MonitorProjectionService {

  public static final Duration DEFAULT_RETENTION = Duration.ofDays(90);

  private final MonitorProjectionPort store;
  private final Duration retention;
  private final Clock clock;

  public MonitorProjectionService(MonitorProjectionPort store) {
    this(store, DEFAULT_RETENTION, Clock.systemUTC());
  }

  public MonitorProjectionService(MonitorProjectionPort store, Duration retention) {
    this(store, retention, Clock.systemUTC());
  }

  public MonitorProjectionService(MonitorProjectionPort store, Duration retention, Clock clock) {
    this.store = store;
    this.retention = retention == null || retention.isNegative() || retention.isZero() ? DEFAULT_RETENTION : retention;
    this.clock = clock == null ? Clock.systemUTC() : clock;
  }

  public boolean available() {
    return store != null;
  }

  public boolean durable() {
    return store != null && store.isDurable();
  }

  public Duration retention() {
    return retention;
  }

  public String recordId(SatelliteInteractionRequest request) {
    return MonitorProjectionIds.eventKey(request);
  }

  public String eventKey(SatelliteInteractionRequest request) {
    return MonitorProjectionIds.eventKey(request);
  }

  public void touchInteraction(
      SatelliteInteractionRequest request,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String technicalState) {
    if (store == null || request == null) {
      return;
    }
    Instant now = clock.instant();
    String interactionId = MonitorProjectionIds.interaction(request);
    if (interactionId != null) {
      upsertInteraction(request, interactionId, type, outcome, technicalState, now);
      recordEventStage(interactionId, MonitorProjectionRecord.KIND_SATELLITE, request, type, outcome, technicalState, now);
    }
    if (MonitorProjectionIds.isListSync(request)) {
      upsertSync(request, type, outcome, technicalState, now);
      String syncId = MonitorProjectionIds.sync(request);
      if (syncId != null) {
        recordEventStage(syncId, MonitorProjectionRecord.KIND_SYNC, request, type, outcome, technicalState, now);
        materializeBackbone(syncId, MonitorProjectionRecord.KIND_SYNC, now, technicalState);
      }
    }
    if (interactionId != null) {
      materializeBackbone(interactionId, MonitorProjectionRecord.KIND_SATELLITE, now, technicalState);
    }
  }

  public void recordReplayPassed(SatelliteInteractionRequest request) {
    if (store == null || request == null) {
      return;
    }
    Instant now = clock.instant();
    String interactionId = MonitorProjectionIds.interaction(request);
    if (interactionId != null) {
      upsertStage(
          stageFromBinding(
              interactionId,
              MonitorJourneyCatalog.replayChecked(),
              now,
              "completed",
              null,
              "REPLAY_CHECK_PASSED",
              Map.of("eventType", "REPLAY_CHECK_PASSED", "decision", "REPLAY_CHECK_PASSED", "source", "satellite-contract")));
      materializeBackbone(interactionId, MonitorProjectionRecord.KIND_SATELLITE, now, "REPLAY_CHECK_PASSED");
    }
    if (MonitorProjectionIds.isListSync(request)) {
      String syncId = MonitorProjectionIds.sync(request);
      if (syncId != null) {
        upsertStage(
            stageFromBinding(
                syncId,
                MonitorJourneyCatalog.replayChecked(),
                now,
                "completed",
                null,
                "REPLAY_CHECK_PASSED",
                Map.of("eventType", "REPLAY_CHECK_PASSED", "decision", "REPLAY_CHECK_PASSED", "source", "satellite-contract")));
        materializeBackbone(syncId, MonitorProjectionRecord.KIND_SYNC, now, "REPLAY_CHECK_PASSED");
      }
    }
  }

  public void recordDiscoveredPayments(SatelliteInteractionRequest request, ExecutionResult result) {
    if (store == null || request == null || result == null || result.quote() == null) {
      return;
    }
    Object raw = result.quote().get("items");
    List<?> items = raw instanceof List<?> list ? list : List.of();
    String companyId = DemoSliceRules.requestedCompanyId(request);
    if (companyId == null || companyId.isBlank()) {
      Object quoteCompany = result.quote().get("companyId");
      companyId = quoteCompany == null ? "" : String.valueOf(quoteCompany);
    }
    String environment = MonitorProjectionIds.environment(request);
    if (environment == null) {
      Object quoteEnv = result.quote().get("environment");
      environment = quoteEnv == null ? null : String.valueOf(quoteEnv);
    }
    Instant now = clock.instant();
    String syncId = MonitorProjectionIds.sync(request);
    String interactionId = MonitorProjectionIds.interaction(request);
    int found = 0;
    int created = 0;
    int updated = 0;
    int ignored = 0;
    for (Object entry : items) {
      if (!(entry instanceof Map<?, ?> row)) {
        continue;
      }
      String transactionId = text(row.get("transactionId"));
      String recordId = MonitorProjectionIds.payment(companyId, transactionId);
      if (recordId == null) {
        ignored++;
        continue;
      }
      found++;
      MonitorProjectionRecord current = store.findById(recordId).orElse(null);
      String financial = MonitorProjectionStates.financial(text(row.get("normalizedStatus")));
      Instant originRevision = parseInstant(row.get("originRevision"));
      if (current != null
          && originRevision != null
          && current.lastSyncedAt() != null
          && originRevision.isBefore(current.lastSyncedAt())
          && !enriches(current, financial)) {
        ignored++;
        continue;
      }
      if (current == null) {
        created++;
      } else {
        updated++;
      }
      String commercial = MonitorProjectionStates.commercial(text(row.get("subscriptionStatus")));
      String credit = MonitorProjectionStates.credit(text(row.get("entitlementStatus")));
      if (credit == null) {
        credit = MonitorProjectionStates.credit(text(row.get("originalStatus")));
      }
      MonitorProjectionRecord incoming =
          MonitorProjectionRecord.builder()
              .recordId(recordId)
              .kind(MonitorProjectionRecord.KIND_PAYMENT)
              .satelliteId(request.satelliteId())
              .satelliteRole(request.satelliteRole())
              .origin(MonitorProjectionRecord.ORIGIN_ACTIONHUB_PAY)
              .messageId(request.messageId())
              .correlationId(request.correlationId())
              .executionId(null)
              .externalRef(transactionId)
              .capability(capabilityOf(request))
              .contractVersion(request.contractVersion())
              .companyId(blankToNull(companyId))
              .environment(environment)
              .technicalState(MonitorProjectionStates.TECH_COMPLETED)
              .commercialState(commercial)
              .financialState(financial)
              .creditState(credit)
              .currentComponent("SPIDER")
              .objective("Pagamento descoberto pelo sincronismo do ActionFinance")
              .createdAt(current == null ? now : current.createdAt())
              .updatedAt(now)
              .lastSyncedAt(originRevision == null ? now : originRevision)
              .discoveryOrigin(MonitorProjectionRecord.DISCOVERY_SYNC)
              .eventKey(recordId)
              .projectionVersion(1)
              .retentionUntil((current == null ? now : current.createdAt()).plus(retention))
              .syncRunId(MonitorProjectionIds.syncRunId(request))
              .relatedSyncId(syncId)
              .relatedInteractionId(interactionId)
              .build();
      store.upsert(incoming);
      recordPaymentJourney(incoming, request, now);
    }
    if (syncId != null) {
      MonitorProjectionRecord current = store.findById(syncId).orElse(null);
      String nextState =
          current == null
              ? MonitorProjectionStates.TECH_PROCESSING
              : current.technicalState();
      if (MonitorProjectionStates.TECH_RECEIVED.equals(nextState)) {
        nextState = MonitorProjectionStates.TECH_PROCESSING;
      }
      store.upsert(
          baseSync(request, now)
              .technicalState(nextState)
              .foundCount((current == null ? 0 : n(current.foundCount())) + found)
              .newCount((current == null ? 0 : n(current.newCount())) + created)
              .updatedCount((current == null ? 0 : n(current.updatedCount())) + updated)
              .ignoredCount((current == null ? 0 : n(current.ignoredCount())) + ignored)
              .build());
      recordSyncDiscoveryStages(syncId, request, found, created, updated, now);
    }
  }

  public int purgeExpired() {
    if (store == null) {
      return 0;
    }
    return store.purgeExpired(clock.instant());
  }

  private void upsertInteraction(
      SatelliteInteractionRequest request,
      String recordId,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String technicalState,
      Instant now) {
    String nextState = MonitorProjectionStates.technical(technicalState, type, outcome);
    String syncId = MonitorProjectionIds.sync(request);
    store.upsert(
        MonitorProjectionRecord.builder()
            .recordId(recordId)
            .kind(MonitorProjectionRecord.KIND_SATELLITE)
            .satelliteId(request.satelliteId())
            .satelliteRole(request.satelliteRole())
            .origin(request.satelliteId())
            .messageId(request.messageId())
            .correlationId(request.correlationId())
            .executionId(null)
            .capability(capabilityOf(request))
            .contractVersion(request.contractVersion())
            .companyId(blankToNull(DemoSliceRules.requestedCompanyId(request)))
            .environment(MonitorProjectionIds.environment(request))
            .technicalState(nextState)
            .financialState(MonitorProjectionStates.FIN_NA)
            .creditState(MonitorProjectionStates.CREDIT_NONE)
            .currentComponent("SPIDER")
            .objective(request.objective() == null ? null : request.objective().text())
            .createdAt(now)
            .updatedAt(now)
            .lastSyncedAt(now)
            .discoveryOrigin(MonitorProjectionRecord.DISCOVERY_DIRECT)
            .eventKey(recordId)
            .retentionUntil(now.plus(retention))
            .syncRunId(MonitorProjectionIds.syncRunId(request))
            .relatedSyncId(syncId)
            .build());
  }

  private void upsertSync(
      SatelliteInteractionRequest request,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String technicalState,
      Instant now) {
    String nextState = MonitorProjectionStates.technical(technicalState, type, outcome);
    Integer page = MonitorProjectionIds.pageNumber(request);
    store.upsert(
        baseSync(request, now)
            .technicalState(nextState)
            .pagesConsulted(page)
            .relatedInteractionId(MonitorProjectionIds.interaction(request))
            .build());
  }

  private MonitorProjectionRecord.Builder baseSync(SatelliteInteractionRequest request, Instant now) {
    String recordId = MonitorProjectionIds.sync(request);
    return MonitorProjectionRecord.builder()
        .recordId(recordId)
        .kind(MonitorProjectionRecord.KIND_SYNC)
        .satelliteId(request.satelliteId())
        .satelliteRole(request.satelliteRole())
        .origin(MonitorProjectionRecord.ORIGIN_ACTIONFINANCE)
        .messageId(request.messageId())
        .correlationId(request.correlationId())
        .executionId(null)
        .capability(capabilityOf(request))
        .contractVersion(request.contractVersion())
        .companyId(blankToNull(DemoSliceRules.requestedCompanyId(request)))
        .environment(MonitorProjectionIds.environment(request))
        .financialState(MonitorProjectionStates.FIN_NA)
        .creditState(MonitorProjectionStates.CREDIT_NONE)
        .currentComponent("SPIDER")
        .objective("Sincronismo de recebimentos")
        .createdAt(now)
        .updatedAt(now)
        .lastSyncedAt(now)
        .discoveryOrigin(MonitorProjectionRecord.DISCOVERY_SYNC)
        .eventKey(recordId)
        .retentionUntil(now.plus(retention))
        .syncRunId(MonitorProjectionIds.syncRunId(request));
  }

  private void recordEventStage(
      String recordId,
      String kind,
      SatelliteInteractionRequest request,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String technicalState,
      Instant now) {
    MonitorJourneyCatalog.Binding binding =
        MonitorJourneyCatalog.forEvent(kind, type, MonitorProjectionIds.pageNumber(request), technicalState);
    if (binding == null) {
      return;
    }
    String executor =
        type == OperationalEventType.OUTBOUND_REQUEST_STARTED
                || type == OperationalEventType.PROVIDER_RESULT_RECEIVED
            ? MonitorJourneyCatalog.sanitizeDecision(technicalState)
            : null;
    if (executor == null && "actionhub-pay".equalsIgnoreCase(technicalState)) {
      executor = "actionhub-pay";
    }
    Map<String, String> evidence = new LinkedHashMap<>();
    evidence.put("eventType", type.name());
    evidence.put("outcome", outcome == null ? null : outcome.name());
    evidence.put("occurredAt", MonitorJourneyEvidence.occurred(now));
    evidence.put("source", "satellite-contract");
    evidence.put("component", binding.componentCode() == null ? "SPIDER" : binding.componentCode());
    evidence.put("componentCode", binding.componentCode() == null ? "SPIDER" : binding.componentCode());
    evidence.put("macroStage", binding.definitionKey());
    evidence.put("participation", MonitorArchitectureBackbone.USED);
    if (executor != null) {
      evidence.put("executor", executor);
    }
    Integer page = MonitorProjectionIds.pageNumber(request);
    if (page != null) {
      evidence.put("page", String.valueOf(page));
    }
    String capability = capabilityOf(request);
    if (capability != null) {
      evidence.put("capability", capability);
    }
    if (MonitorProjectionIds.syncRunId(request) != null) {
      evidence.put("syncRunId", MonitorProjectionIds.syncRunId(request));
    }
    String decision = MonitorJourneyCatalog.sanitizeDecision(technicalState);
    if (decision != null) {
      evidence.put("decision", decision);
    }
    String state = MonitorJourneyCatalog.stageState(outcome, technicalState, type);
    upsertStage(
        MonitorJourneyStage.builder()
            .recordId(recordId)
            .stageId(binding.stageId())
            .stageType(binding.stageType())
            .sortOrder(binding.sortOrder())
            .state(state)
            .component(binding.componentCode() == null ? "SPIDER" : binding.componentCode())
            .executor(executor)
            .occurredAt(now)
            .completedAt("completed".equals(state) || "failed".equals(state) || "rejected".equals(state) ? now : null)
            .title(binding.title())
            .definitionKey(binding.definitionKey())
            .decision(decision)
            .eventType(type.name())
            .evidenceJson(MonitorJourneyEvidence.append(null, evidence))
            .build());
    completePriorStages(recordId, binding.sortOrder(), now);
  }

  private void completePriorStages(String recordId, int beforeOrder, Instant now) {
    for (MonitorJourneyStage stage : store.findStages(recordId)) {
      if (stage.sortOrder() >= beforeOrder || !"running".equals(stage.state())) {
        continue;
      }
      upsertStage(stage.toBuilder().state("completed").completedAt(now).build());
    }
  }

  private void recordPaymentJourney(MonitorProjectionRecord payment, SatelliteInteractionRequest request, Instant now) {
    String syncRunId = MonitorProjectionIds.syncRunId(request);
    upsertStage(stageFromBinding(payment.recordId(), MonitorJourneyCatalog.paymentObserved(), now, "completed", "actionhub-pay",
        "Operação observada no ActionHub Pay", Map.of("eventType", "PAYMENT_OBSERVED", "source", "actionhub-pay")));
    MonitorJourneyStage discovered =
        stageFromBinding(
            payment.recordId(),
            MonitorJourneyCatalog.paymentDiscovered(),
            now,
            "completed",
            null,
            syncRunId,
            Map.of("eventType", "PAYMENT_DISCOVERED", "syncRunId", syncRunId == null ? "" : syncRunId));
    upsertStage(
        syncRunId == null
            ? discovered
            : discovered.toBuilder().title("Descoberta pelo sincronismo " + syncRunId).build());
    upsertStage(stageFromBinding(payment.recordId(), MonitorJourneyCatalog.paymentCorrelated(), now, "completed", null,
        MonitorProjectionIds.maskExternal(payment.externalRef()), Map.of("eventType", "PAYMENT_CORRELATED")));
    upsertStage(stageFromBinding(payment.recordId(), MonitorJourneyCatalog.paymentFinancial(), now, "completed", null,
        payment.financialState(), Map.of("eventType", "FINANCIAL_STATE", "decision", nvl(payment.financialState()))));
  }

  private void recordSyncDiscoveryStages(
      String syncId, SatelliteInteractionRequest request, int found, int created, int updated, Instant now) {
    upsertStage(stageFromBinding(syncId, MonitorJourneyCatalog.syncPaymentsCorrelated(), now, "completed", "actionhub-pay",
        found + " pagamento(s) correlacionado(s)",
        Map.of("eventType", "PAYMENTS_CORRELATED", "foundCount", String.valueOf(found))));
    upsertStage(stageFromBinding(syncId, MonitorJourneyCatalog.syncProjectionsUpserted(), now, "completed", "SPIDER",
        created + " criadas / " + updated + " atualizadas",
        Map.of("eventType", "PROJECTIONS_UPSERTED", "newCount", String.valueOf(created), "updatedCount", String.valueOf(updated))));
    upsertStage(stageFromBinding(syncId, MonitorJourneyCatalog.syncCountsRecorded(), now, "completed", "SPIDER",
        "Contagens registradas",
        Map.of("eventType", "COUNTS_RECORDED", "foundCount", String.valueOf(found))));
  }

  private MonitorJourneyStage stageFromBinding(
      String recordId,
      MonitorJourneyCatalog.Binding binding,
      Instant now,
      String state,
      String executor,
      String decision,
      Map<String, String> evidence) {
    Map<String, String> payload = new LinkedHashMap<>(evidence);
    payload.put("occurredAt", MonitorJourneyEvidence.occurred(now));
    payload.put("outcome", "SUCCESS");
    if (executor != null) {
      payload.put("executor", executor);
    }
    return MonitorJourneyStage.builder()
        .recordId(recordId)
        .stageId(binding.stageId())
        .stageType(binding.stageType())
        .sortOrder(binding.sortOrder())
        .state(state)
        .component(binding.componentCode() == null ? "SPIDER" : binding.componentCode())
        .executor(executor)
        .occurredAt(now)
        .completedAt(now)
        .title(binding.title())
        .definitionKey(binding.definitionKey())
        .decision(MonitorJourneyCatalog.sanitizeDecision(decision))
        .eventType(binding.stageType())
        .evidenceJson(MonitorJourneyEvidence.append(null, payload))
        .build();
  }

  private void materializeBackbone(String recordId, String kind, Instant now, String reason) {
    if (recordId == null || recordId.isBlank()) {
      return;
    }
    List<MonitorArchitectureBackbone.Slot> slots = MonitorArchitectureBackbone.forKind(kind);
    if (slots.isEmpty()) {
      return;
    }
    List<MonitorJourneyStage> observed = store.findStages(recordId);
    java.util.Map<String, MonitorJourneyStage> byId = new LinkedHashMap<>();
    for (MonitorJourneyStage stage : observed) {
      byId.put(stage.stageId(), stage);
    }
    MonitorJourneyStage interrupt =
        observed.stream()
            .filter(stage -> "rejected".equals(stage.state()) || "failed".equals(stage.state()))
            .filter(stage -> MonitorArchitectureBackbone.usedState(stage.state()))
            .min(java.util.Comparator.comparingInt(MonitorJourneyStage::sortOrder))
            .orElse(null);
    boolean terminal =
        observed.stream()
            .anyMatch(
                stage ->
                    MonitorJourneyCatalog.availability(List.of(stage)).equals(MonitorJourneyStage.AVAILABILITY_COMPLETE)
                        || "rejected".equals(stage.state())
                        || "failed".equals(stage.state()));
    String interruptReason =
        interrupt != null && interrupt.decision() != null
            ? interrupt.decision()
            : MonitorJourneyCatalog.sanitizeDecision(reason);
    String notReachedReason =
        interruptReason == null || interruptReason.isBlank()
            ? "Processamento interrompido antes desta etapa."
            : notReachedMessage(interruptReason, interrupt == null ? null : interrupt.stageId());
    for (MonitorArchitectureBackbone.Slot slot : slots) {
      MonitorJourneyStage existing = byId.get(slot.stageId());
      if (existing != null && MonitorArchitectureBackbone.usedState(existing.state())) {
        continue;
      }
      if (MonitorArchitectureBackbone.unusedOnThisPath(slot)) {
        upsertStage(structuralStage(recordId, slot, now, MonitorArchitectureBackbone.STATE_NOT_USED, slot.unusedReason()));
        continue;
      }
      if (isObserveSlot(slot)) {
        upsertStage(
            structuralStage(
                recordId,
                slot,
                now,
                "completed",
                "Projeção persistida na versão " + MonitorJourneyStage.JOURNEY_PROJECTION_VERSION + "."));
        continue;
      }
      if (existing != null) {
        continue;
      }
      if (interrupt != null && slot.sortOrder() > interrupt.sortOrder()) {
        upsertStage(structuralStage(recordId, slot, now, MonitorArchitectureBackbone.STATE_NOT_REACHED, notReachedReason));
        continue;
      }
      if (terminal) {
        upsertStage(structuralStage(recordId, slot, now, MonitorArchitectureBackbone.STATE_NOT_REACHED, notReachedReason));
      }
    }
  }

  private static boolean isObserveSlot(MonitorArchitectureBackbone.Slot slot) {
    return slot != null
        && ("observe".equals(slot.macroStage())
            || "persistence_ports".equals(slot.stageId())
            || "operational_events".equals(slot.stageId())
            || "monitor_query".equals(slot.stageId()));
  }

  private static String notReachedMessage(String reason, String stageId) {
    if ("contract_validated".equals(stageId) || "INVALID_PAYLOAD".equals(reason) || "INVALID_CONTRACT_VERSION".equals(reason)) {
      return "NÃO ALCANÇADA — processamento interrompido na validação do contrato.";
    }
    if ("NO_COMPANY_BINDING".equals(reason) || "UNAUTHORIZED_SATELLITE".equals(reason)) {
      return "NÃO ALCANÇADA — empresa ou satélite não autorizado; ActionHub Pay não foi chamado.";
    }
    return "NÃO ALCANÇADA — processamento interrompido (" + reason + ").";
  }

  private MonitorJourneyStage structuralStage(
      String recordId, MonitorArchitectureBackbone.Slot slot, Instant now, String state, String decision) {
    String participation = MonitorArchitectureBackbone.participationOf(state);
    Map<String, String> evidence = new LinkedHashMap<>();
    evidence.put("eventType", slot.stageType());
    evidence.put("occurredAt", MonitorJourneyEvidence.occurred(now));
    evidence.put("source", "monitor-backbone");
    evidence.put("component", slot.componentCode());
    evidence.put("componentCode", slot.componentCode());
    evidence.put("macroStage", slot.macroStage());
    evidence.put("participation", participation);
    evidence.put("decision", decision == null ? "" : decision);
    evidence.put("reason", decision == null ? "" : decision);
    evidence.put("outcome", "completed".equals(state) ? "SUCCESS" : state.toUpperCase());
    return MonitorJourneyStage.builder()
        .recordId(recordId)
        .stageId(slot.stageId())
        .stageType(slot.stageType())
        .sortOrder(slot.sortOrder())
        .state(state)
        .component(slot.componentCode())
        .occurredAt(now)
        .completedAt("completed".equals(state) || "rejected".equals(state) || "failed".equals(state) ? now : now)
        .title(slot.title())
        .definitionKey(slot.macroStage())
        .decision(MonitorJourneyCatalog.sanitizeDecision(decision))
        .eventType(slot.stageType())
        .evidenceJson(MonitorJourneyEvidence.append(null, evidence))
        .build();
  }

  private void upsertStage(MonitorJourneyStage stage) {
    store.upsertStage(stage);
  }

  private static String nvl(String value) {
    return value == null ? "" : value;
  }

  private static boolean enriches(MonitorProjectionRecord current, String financial) {
    return (current.financialState() == null
            || current.financialState().isBlank()
            || MonitorProjectionStates.FIN_UNKNOWN.equals(current.financialState()))
        && financial != null
        && !financial.isBlank()
        && !MonitorProjectionStates.FIN_UNKNOWN.equals(financial);
  }

  private static String capabilityOf(SatelliteInteractionRequest request) {
    if (request == null || request.purpose() == null) {
      return null;
    }
    if (SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LIST.equals(request.purpose())) {
      return SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS;
    }
    if (SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LOOKUP.equals(request.purpose())) {
      return SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT;
    }
    return request.purpose();
  }

  private static Instant parseInstant(Object value) {
    if (value == null) {
      return null;
    }
    try {
      return Instant.parse(String.valueOf(value));
    } catch (RuntimeException ignored) {
      return null;
    }
  }

  private static String text(Object value) {
    return value == null ? "" : String.valueOf(value).trim();
  }

  private static String blankToNull(String value) {
    return value == null || value.isBlank() ? null : value;
  }

  private static int n(Integer value) {
    return value == null ? 0 : value;
  }
}
