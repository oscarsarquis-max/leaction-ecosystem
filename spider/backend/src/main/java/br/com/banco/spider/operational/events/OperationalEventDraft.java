package br.com.banco.spider.operational.events;

import java.util.Objects;

public record OperationalEventDraft(
    OperationalEventType eventType,
    String executionId,
    String interactionId,
    String correlationId,
    String source,
    OperationalEventOutcome outcome,
    Long durationMs,
    OperationalEventAttributes attributes) {

  public OperationalEventDraft {
    Objects.requireNonNull(eventType, "eventType");
    Objects.requireNonNull(source, "source");
    attributes = attributes == null ? OperationalEventAttributes.empty() : attributes;
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private OperationalEventType eventType;
    private String executionId;
    private String interactionId;
    private String correlationId;
    private String source;
    private OperationalEventOutcome outcome;
    private Long durationMs;
    private OperationalEventAttributes attributes = OperationalEventAttributes.empty();

    public Builder eventType(OperationalEventType value) {
      eventType = value;
      return this;
    }

    public Builder executionId(String value) {
      executionId = value;
      return this;
    }

    public Builder interactionId(String value) {
      interactionId = value;
      return this;
    }

    public Builder correlationId(String value) {
      correlationId = value;
      return this;
    }

    public Builder source(String value) {
      source = value;
      return this;
    }

    public Builder outcome(OperationalEventOutcome value) {
      outcome = value;
      return this;
    }

    public Builder durationMs(Long value) {
      durationMs = value;
      return this;
    }

    public Builder attributes(OperationalEventAttributes value) {
      attributes = value;
      return this;
    }

    public OperationalEventDraft build() {
      return new OperationalEventDraft(
          eventType,
          executionId,
          interactionId,
          correlationId,
          source,
          outcome,
          durationMs,
          attributes);
    }
  }
}
