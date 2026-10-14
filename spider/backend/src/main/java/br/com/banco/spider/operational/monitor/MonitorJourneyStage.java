package br.com.banco.spider.operational.monitor;

import java.time.Instant;

public record MonitorJourneyStage(
    String recordId,
    String stageId,
    String stageType,
    int sortOrder,
    String state,
    String component,
    String executor,
    Instant occurredAt,
    Instant completedAt,
    String title,
    String definitionKey,
    String decision,
    String eventType,
    String evidenceJson,
    Integer attempt,
    int projectionVersion) {

  public static final int JOURNEY_PROJECTION_VERSION = 3;
  public static final String PERSISTED_SINCE_VERSION = "V20261016";
  public static final String PERSISTED_SINCE_DATE = "2026-10-13";
  public static final String AVAILABILITY_COMPLETE = "COMPLETE";
  public static final String AVAILABILITY_PARTIAL = "PARTIAL";
  public static final String AVAILABILITY_UNAVAILABLE = "UNAVAILABLE";
  public static final String HISTORICAL_NOTICE =
      "Percurso não disponível para este registro anterior à persistência das etapas.";

  public Builder toBuilder() {
    return new Builder(this);
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private String recordId;
    private String stageId;
    private String stageType;
    private int sortOrder;
    private String state;
    private String component;
    private String executor;
    private Instant occurredAt;
    private Instant completedAt;
    private String title;
    private String definitionKey;
    private String decision;
    private String eventType;
    private String evidenceJson;
    private Integer attempt;
    private int projectionVersion = JOURNEY_PROJECTION_VERSION;

    private Builder() {}

    private Builder(MonitorJourneyStage source) {
      this.recordId = source.recordId;
      this.stageId = source.stageId;
      this.stageType = source.stageType;
      this.sortOrder = source.sortOrder;
      this.state = source.state;
      this.component = source.component;
      this.executor = source.executor;
      this.occurredAt = source.occurredAt;
      this.completedAt = source.completedAt;
      this.title = source.title;
      this.definitionKey = source.definitionKey;
      this.decision = source.decision;
      this.eventType = source.eventType;
      this.evidenceJson = source.evidenceJson;
      this.attempt = source.attempt;
      this.projectionVersion = source.projectionVersion;
    }

    public Builder recordId(String value) { this.recordId = value; return this; }
    public Builder stageId(String value) { this.stageId = value; return this; }
    public Builder stageType(String value) { this.stageType = value; return this; }
    public Builder sortOrder(int value) { this.sortOrder = value; return this; }
    public Builder state(String value) { this.state = value; return this; }
    public Builder component(String value) { this.component = value; return this; }
    public Builder executor(String value) { this.executor = value; return this; }
    public Builder occurredAt(Instant value) { this.occurredAt = value; return this; }
    public Builder completedAt(Instant value) { this.completedAt = value; return this; }
    public Builder title(String value) { this.title = value; return this; }
    public Builder definitionKey(String value) { this.definitionKey = value; return this; }
    public Builder decision(String value) { this.decision = value; return this; }
    public Builder eventType(String value) { this.eventType = value; return this; }
    public Builder evidenceJson(String value) { this.evidenceJson = value; return this; }
    public Builder attempt(Integer value) { this.attempt = value; return this; }
    public Builder projectionVersion(int value) { this.projectionVersion = value; return this; }

    public MonitorJourneyStage build() {
      return new MonitorJourneyStage(
          recordId, stageId, stageType, sortOrder, state, component, executor, occurredAt, completedAt,
          title, definitionKey, decision, eventType, evidenceJson, attempt, projectionVersion);
    }
  }
}
