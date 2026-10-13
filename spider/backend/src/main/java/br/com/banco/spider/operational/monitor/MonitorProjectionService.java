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
    }
    if (MonitorProjectionIds.isListSync(request)) {
      upsertSync(request, type, outcome, technicalState, now);
    }
  }

  public void recordDiscoveredPayments(SatelliteInteractionRequest request, ExecutionResult result) {
    if (store == null || request == null || result == null || result.quote() == null) {
      return;
    }
    Object raw = result.quote().get("items");
    if (!(raw instanceof List<?> items)) {
      return;
    }
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
    }
    if (syncId != null) {
      MonitorProjectionRecord current = store.findById(syncId).orElse(null);
      store.upsert(
          baseSync(request, now)
              .technicalState(
                  current == null
                      ? MonitorProjectionStates.TECH_PROCESSING
                      : current.technicalState())
              .foundCount((current == null ? 0 : n(current.foundCount())) + found)
              .newCount((current == null ? 0 : n(current.newCount())) + created)
              .updatedCount((current == null ? 0 : n(current.updatedCount())) + updated)
              .ignoredCount((current == null ? 0 : n(current.ignoredCount())) + ignored)
              .build());
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
