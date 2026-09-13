package br.com.segsense.infrastructure.link;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

@Entity
@Immutable
@Table(name = "published_context_link_event", schema = "segsense")
public class PublishedContextLinkEventJpaEntity {

  @Id private UUID id;

  @Column(name = "link_id", nullable = false)
  private UUID linkId;

  @Column(name = "event_type", nullable = false, length = 16)
  private String eventType;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(name = "actor_subject", nullable = false, length = 128)
  private String actorSubject;

  @Column(name = "correlation_id", nullable = false)
  private UUID correlationId;

  protected PublishedContextLinkEventJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getLinkId() {
    return linkId;
  }

  public void setLinkId(UUID linkId) {
    this.linkId = linkId;
  }

  public String getEventType() {
    return eventType;
  }

  public void setEventType(String eventType) {
    this.eventType = eventType;
  }

  public Instant getOccurredAt() {
    return occurredAt;
  }

  public void setOccurredAt(Instant occurredAt) {
    this.occurredAt = occurredAt;
  }

  public String getActorSubject() {
    return actorSubject;
  }

  public void setActorSubject(String actorSubject) {
    this.actorSubject = actorSubject;
  }

  public UUID getCorrelationId() {
    return correlationId;
  }

  public void setCorrelationId(UUID correlationId) {
    this.correlationId = correlationId;
  }
}
