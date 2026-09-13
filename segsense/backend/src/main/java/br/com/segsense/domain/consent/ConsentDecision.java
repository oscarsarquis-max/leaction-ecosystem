package br.com.segsense.domain.consent;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class ConsentDecision {

  public static final String PUBLIC_ANONYMOUS = "PUBLIC_ANONYMOUS";

  private final UUID id;
  private final UUID instanceId;
  private final ConsentDecisionType decisionType;
  private final int noticeVersion;
  private final String noticeContentHash;
  private final String coveredFieldsHash;
  private final Instant occurredAt;
  private final UUID correlationId;
  private final long instanceVersionBefore;
  private final long instanceVersionAfter;
  private final String actor;

  private ConsentDecision(
      UUID id,
      UUID instanceId,
      ConsentDecisionType decisionType,
      int noticeVersion,
      String noticeContentHash,
      String coveredFieldsHash,
      Instant occurredAt,
      UUID correlationId,
      long instanceVersionBefore,
      long instanceVersionAfter,
      String actor) {
    this.id = id;
    this.instanceId = instanceId;
    this.decisionType = decisionType;
    this.noticeVersion = noticeVersion;
    this.noticeContentHash = noticeContentHash;
    this.coveredFieldsHash = coveredFieldsHash;
    this.occurredAt = occurredAt;
    this.correlationId = correlationId;
    this.instanceVersionBefore = instanceVersionBefore;
    this.instanceVersionAfter = instanceVersionAfter;
    this.actor = actor;
  }

  public static ConsentDecision record(
      UUID id,
      UUID instanceId,
      ConsentDecisionType decisionType,
      int noticeVersion,
      String noticeContentHash,
      String coveredFieldsHash,
      Instant occurredAt,
      UUID correlationId,
      long instanceVersionBefore,
      long instanceVersionAfter) {
    return new ConsentDecision(
        Objects.requireNonNull(id, "id"),
        Objects.requireNonNull(instanceId, "instanceId"),
        Objects.requireNonNull(decisionType, "decisionType"),
        noticeVersion,
        Objects.requireNonNull(noticeContentHash, "noticeContentHash"),
        Objects.requireNonNull(coveredFieldsHash, "coveredFieldsHash"),
        Objects.requireNonNull(occurredAt, "occurredAt"),
        Objects.requireNonNull(correlationId, "correlationId"),
        instanceVersionBefore,
        instanceVersionAfter,
        PUBLIC_ANONYMOUS);
  }

  public UUID id() {
    return id;
  }

  public UUID instanceId() {
    return instanceId;
  }

  public ConsentDecisionType decisionType() {
    return decisionType;
  }

  public int noticeVersion() {
    return noticeVersion;
  }

  public String noticeContentHash() {
    return noticeContentHash;
  }

  public String coveredFieldsHash() {
    return coveredFieldsHash;
  }

  public Instant occurredAt() {
    return occurredAt;
  }

  public UUID correlationId() {
    return correlationId;
  }

  public long instanceVersionBefore() {
    return instanceVersionBefore;
  }

  public long instanceVersionAfter() {
    return instanceVersionAfter;
  }

  public String actor() {
    return actor;
  }
}
