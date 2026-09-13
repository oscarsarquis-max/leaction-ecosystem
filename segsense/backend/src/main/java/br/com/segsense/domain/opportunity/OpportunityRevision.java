package br.com.segsense.domain.opportunity;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class OpportunityRevision {

  private final UUID id;
  private final int revisionNumber;
  private final OpportunityContent content;
  private final Instant createdAt;
  private final String createdBy;

  public OpportunityRevision(
      UUID id, int revisionNumber, OpportunityContent content, Instant createdAt, String createdBy) {
    if (revisionNumber < 1) {
      throw new IllegalArgumentException("revisionNumber");
    }
    this.id = Objects.requireNonNull(id, "id");
    this.revisionNumber = revisionNumber;
    this.content = Objects.requireNonNull(content, "content");
    this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
    this.createdBy = Objects.requireNonNull(createdBy, "createdBy");
  }

  public UUID id() {
    return id;
  }

  public int revisionNumber() {
    return revisionNumber;
  }

  public OpportunityContent content() {
    return content;
  }

  public Instant createdAt() {
    return createdAt;
  }

  public String createdBy() {
    return createdBy;
  }
}
