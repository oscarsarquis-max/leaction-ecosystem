package br.com.banco.spider.operational.monitor;

import java.time.Instant;

public record MonitorProjectionRecord(
    String recordId,
    String kind,
    String satelliteId,
    String satelliteRole,
    String origin,
    String messageId,
    String correlationId,
    String executionId,
    String externalRef,
    String capability,
    String contractVersion,
    String companyId,
    String environment,
    String technicalState,
    String commercialState,
    String financialState,
    String creditState,
    String currentComponent,
    String objective,
    Instant createdAt,
    Instant updatedAt,
    Instant lastSyncedAt,
    String discoveryOrigin,
    String eventKey,
    int projectionVersion,
    Instant retentionUntil,
    String syncRunId,
    String relatedSyncId,
    String relatedPaymentId,
    String relatedInteractionId,
    Integer pagesConsulted,
    Integer foundCount,
    Integer newCount,
    Integer updatedCount,
    Integer ignoredCount,
    Integer failedCount) {

  public static final String KIND_SATELLITE = "SATELLITE_INTERACTION";
  public static final String KIND_SYNC = "SYNC_EXECUTION";
  public static final String KIND_PAYMENT = "DISCOVERED_PAYMENT";
  public static final String KIND_CANONICAL = "CANONICAL_EXECUTION";
  public static final String DISCOVERY_DIRECT = "DIRECT_INTERACTION";
  public static final String DISCOVERY_SYNC = "SYNC_DISCOVERY";
  public static final String ORIGIN_ACTIONFINANCE = "actionfinance";
  public static final String ORIGIN_ACTIONHUB_PAY = "actionhub-pay";

  public Builder toBuilder() {
    return new Builder(this);
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private String recordId;
    private String kind;
    private String satelliteId;
    private String satelliteRole;
    private String origin;
    private String messageId;
    private String correlationId;
    private String executionId;
    private String externalRef;
    private String capability;
    private String contractVersion;
    private String companyId;
    private String environment;
    private String technicalState;
    private String commercialState;
    private String financialState;
    private String creditState;
    private String currentComponent;
    private String objective;
    private Instant createdAt;
    private Instant updatedAt;
    private Instant lastSyncedAt;
    private String discoveryOrigin;
    private String eventKey;
    private int projectionVersion = 1;
    private Instant retentionUntil;
    private String syncRunId;
    private String relatedSyncId;
    private String relatedPaymentId;
    private String relatedInteractionId;
    private Integer pagesConsulted;
    private Integer foundCount;
    private Integer newCount;
    private Integer updatedCount;
    private Integer ignoredCount;
    private Integer failedCount;

    private Builder() {}

    private Builder(MonitorProjectionRecord source) {
      this.recordId = source.recordId;
      this.kind = source.kind;
      this.satelliteId = source.satelliteId;
      this.satelliteRole = source.satelliteRole;
      this.origin = source.origin;
      this.messageId = source.messageId;
      this.correlationId = source.correlationId;
      this.executionId = source.executionId;
      this.externalRef = source.externalRef;
      this.capability = source.capability;
      this.contractVersion = source.contractVersion;
      this.companyId = source.companyId;
      this.environment = source.environment;
      this.technicalState = source.technicalState;
      this.commercialState = source.commercialState;
      this.financialState = source.financialState;
      this.creditState = source.creditState;
      this.currentComponent = source.currentComponent;
      this.objective = source.objective;
      this.createdAt = source.createdAt;
      this.updatedAt = source.updatedAt;
      this.lastSyncedAt = source.lastSyncedAt;
      this.discoveryOrigin = source.discoveryOrigin;
      this.eventKey = source.eventKey;
      this.projectionVersion = source.projectionVersion;
      this.retentionUntil = source.retentionUntil;
      this.syncRunId = source.syncRunId;
      this.relatedSyncId = source.relatedSyncId;
      this.relatedPaymentId = source.relatedPaymentId;
      this.relatedInteractionId = source.relatedInteractionId;
      this.pagesConsulted = source.pagesConsulted;
      this.foundCount = source.foundCount;
      this.newCount = source.newCount;
      this.updatedCount = source.updatedCount;
      this.ignoredCount = source.ignoredCount;
      this.failedCount = source.failedCount;
    }

    public Builder recordId(String value) { this.recordId = value; return this; }
    public Builder kind(String value) { this.kind = value; return this; }
    public Builder satelliteId(String value) { this.satelliteId = value; return this; }
    public Builder satelliteRole(String value) { this.satelliteRole = value; return this; }
    public Builder origin(String value) { this.origin = value; return this; }
    public Builder messageId(String value) { this.messageId = value; return this; }
    public Builder correlationId(String value) { this.correlationId = value; return this; }
    public Builder executionId(String value) { this.executionId = value; return this; }
    public Builder externalRef(String value) { this.externalRef = value; return this; }
    public Builder capability(String value) { this.capability = value; return this; }
    public Builder contractVersion(String value) { this.contractVersion = value; return this; }
    public Builder companyId(String value) { this.companyId = value; return this; }
    public Builder environment(String value) { this.environment = value; return this; }
    public Builder technicalState(String value) { this.technicalState = value; return this; }
    public Builder commercialState(String value) { this.commercialState = value; return this; }
    public Builder financialState(String value) { this.financialState = value; return this; }
    public Builder creditState(String value) { this.creditState = value; return this; }
    public Builder currentComponent(String value) { this.currentComponent = value; return this; }
    public Builder objective(String value) { this.objective = value; return this; }
    public Builder createdAt(Instant value) { this.createdAt = value; return this; }
    public Builder updatedAt(Instant value) { this.updatedAt = value; return this; }
    public Builder lastSyncedAt(Instant value) { this.lastSyncedAt = value; return this; }
    public Builder discoveryOrigin(String value) { this.discoveryOrigin = value; return this; }
    public Builder eventKey(String value) { this.eventKey = value; return this; }
    public Builder projectionVersion(int value) { this.projectionVersion = value; return this; }
    public Builder retentionUntil(Instant value) { this.retentionUntil = value; return this; }
    public Builder syncRunId(String value) { this.syncRunId = value; return this; }
    public Builder relatedSyncId(String value) { this.relatedSyncId = value; return this; }
    public Builder relatedPaymentId(String value) { this.relatedPaymentId = value; return this; }
    public Builder relatedInteractionId(String value) { this.relatedInteractionId = value; return this; }
    public Builder pagesConsulted(Integer value) { this.pagesConsulted = value; return this; }
    public Builder foundCount(Integer value) { this.foundCount = value; return this; }
    public Builder newCount(Integer value) { this.newCount = value; return this; }
    public Builder updatedCount(Integer value) { this.updatedCount = value; return this; }
    public Builder ignoredCount(Integer value) { this.ignoredCount = value; return this; }
    public Builder failedCount(Integer value) { this.failedCount = value; return this; }

    public MonitorProjectionRecord build() {
      return new MonitorProjectionRecord(
          recordId, kind, satelliteId, satelliteRole, origin, messageId, correlationId, executionId,
          externalRef, capability, contractVersion, companyId, environment, technicalState,
          commercialState, financialState, creditState, currentComponent, objective, createdAt,
          updatedAt, lastSyncedAt, discoveryOrigin, eventKey, projectionVersion, retentionUntil,
          syncRunId, relatedSyncId, relatedPaymentId, relatedInteractionId, pagesConsulted,
          foundCount, newCount, updatedCount, ignoredCount, failedCount);
    }
  }
}
