package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_operational_event")
@Getter
@Setter
@NoArgsConstructor
public class OperationalEventEntity {

  @Id
  @Column(name = "event_id", length = 120)
  private String eventId;

  @Column(name = "schema_version", nullable = false)
  private int schemaVersion;

  @Enumerated(EnumType.STRING)
  @Column(name = "event_type", nullable = false, length = 80)
  private br.com.banco.spider.operational.events.OperationalEventType eventType;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private br.com.banco.spider.operational.events.OperationalEventCategory category;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(name = "execution_id", nullable = false, length = 120)
  private String executionId;

  @Column(name = "interaction_id", length = 120)
  private String interactionId;

  @Column(name = "correlation_id", length = 200)
  private String correlationId;

  @Column(nullable = false, length = 120)
  private String source;

  @Enumerated(EnumType.STRING)
  @Column(length = 40)
  private br.com.banco.spider.operational.events.OperationalEventOutcome outcome;

  @Column(name = "duration_ms")
  private Long durationMs;

  @Column(name = "metadata_json", nullable = false, columnDefinition = "text")
  private String metadataJson;
}
