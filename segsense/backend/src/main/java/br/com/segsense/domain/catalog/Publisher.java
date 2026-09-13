package br.com.segsense.domain.catalog;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class Publisher {

  private final UUID id;
  private final ResourceKey key;
  private DisplayName name;
  private LifecycleStatus status;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;

  private Publisher(
      UUID id,
      ResourceKey key,
      DisplayName name,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    this.id = Objects.requireNonNull(id, "id");
    this.key = Objects.requireNonNull(key, "key");
    this.name = Objects.requireNonNull(name, "name");
    this.status = Objects.requireNonNull(status, "status");
    this.version = version;
    this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
    this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt");
    this.createdBy = requireSubject(createdBy, "createdBy");
    this.updatedBy = requireSubject(updatedBy, "updatedBy");
  }

  public static Publisher create(
      UUID id, ResourceKey key, DisplayName name, Instant now, String actorSubject) {
    String subject = requireSubject(actorSubject, "createdBy");
    Instant timestamp = Objects.requireNonNull(now, "now");
    return new Publisher(
        id, key, name, LifecycleStatus.DRAFT, 0L, timestamp, timestamp, subject, subject);
  }

  public static Publisher restore(
      UUID id,
      ResourceKey key,
      DisplayName name,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    return new Publisher(
        id, key, name, status, version, createdAt, updatedAt, createdBy, updatedBy);
  }

  public void rename(DisplayName newName, Instant now, String actorSubject) {
    this.name = Objects.requireNonNull(newName, "name");
    touch(now, actorSubject);
  }

  public void transitionTo(LifecycleStatus target, Instant now, String actorSubject) {
    Objects.requireNonNull(target, "target");
    if (!status.canTransitionTo(target)) {
      throw new InvalidStateTransitionException();
    }
    this.status = target;
    touch(now, actorSubject);
  }

  public void requireExpectedVersion(long expectedVersion) {
    if (this.version != expectedVersion) {
      throw new OptimisticConcurrencyException();
    }
  }

  public boolean effectivelyAvailable() {
    return status == LifecycleStatus.ACTIVE;
  }

  private void touch(Instant now, String actorSubject) {
    this.updatedAt = Objects.requireNonNull(now, "now");
    this.updatedBy = requireSubject(actorSubject, "updatedBy");
  }

  private static String requireSubject(String subject, String field) {
    if (subject == null || subject.isBlank()) {
      throw new CatalogValidationException("A autoria técnica é obrigatória.");
    }
    String normalized = subject.trim();
    if (normalized.length() > 128) {
      throw new CatalogValidationException("A autoria técnica é inválida.");
    }
    return normalized;
  }

  public UUID id() {
    return id;
  }

  public ResourceKey key() {
    return key;
  }

  public DisplayName name() {
    return name;
  }

  public LifecycleStatus status() {
    return status;
  }

  public long version() {
    return version;
  }

  public Instant createdAt() {
    return createdAt;
  }

  public Instant updatedAt() {
    return updatedAt;
  }

  public String createdBy() {
    return createdBy;
  }

  public String updatedBy() {
    return updatedBy;
  }
}
