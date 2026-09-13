package br.com.segsense.domain.catalog;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class Channel {

  private final UUID id;
  private final UUID publisherId;
  private final ResourceKey key;
  private DisplayName name;
  private final ChannelType type;
  private LifecycleStatus status;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;

  private Channel(
      UUID id,
      UUID publisherId,
      ResourceKey key,
      DisplayName name,
      ChannelType type,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    this.id = Objects.requireNonNull(id, "id");
    this.publisherId = Objects.requireNonNull(publisherId, "publisherId");
    this.key = Objects.requireNonNull(key, "key");
    this.name = Objects.requireNonNull(name, "name");
    this.type = Objects.requireNonNull(type, "type");
    this.status = Objects.requireNonNull(status, "status");
    this.version = version;
    this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
    this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt");
    this.createdBy = requireSubject(createdBy);
    this.updatedBy = requireSubject(updatedBy);
  }

  public static Channel create(
      UUID id,
      Publisher publisher,
      ResourceKey key,
      DisplayName name,
      ChannelType type,
      Instant now,
      String actorSubject) {
    Objects.requireNonNull(publisher, "publisher");
    String subject = requireSubject(actorSubject);
    Instant timestamp = Objects.requireNonNull(now, "now");
    return new Channel(
        id,
        publisher.id(),
        key,
        name,
        type,
        LifecycleStatus.DRAFT,
        0L,
        timestamp,
        timestamp,
        subject,
        subject);
  }

  public static Channel restore(
      UUID id,
      UUID publisherId,
      ResourceKey key,
      DisplayName name,
      ChannelType type,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    return new Channel(
        id,
        publisherId,
        key,
        name,
        type,
        status,
        version,
        createdAt,
        updatedAt,
        createdBy,
        updatedBy);
  }

  public void rename(DisplayName newName, Instant now, String actorSubject) {
    this.name = Objects.requireNonNull(newName, "name");
    touch(now, actorSubject);
  }

  public void transitionTo(LifecycleStatus target, Publisher publisher, Instant now, String actorSubject) {
    Objects.requireNonNull(target, "target");
    Objects.requireNonNull(publisher, "publisher");
    if (!publisher.id().equals(publisherId)) {
      throw new ResourceNotFoundException();
    }
    if (!status.canTransitionTo(target)) {
      throw new InvalidStateTransitionException();
    }
    if (target == LifecycleStatus.ACTIVE && publisher.status() != LifecycleStatus.ACTIVE) {
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

  public boolean effectivelyAvailable(Publisher publisher) {
    Objects.requireNonNull(publisher, "publisher");
    return status == LifecycleStatus.ACTIVE && publisher.effectivelyAvailable();
  }

  private void touch(Instant now, String actorSubject) {
    this.updatedAt = Objects.requireNonNull(now, "now");
    this.updatedBy = requireSubject(actorSubject);
  }

  private static String requireSubject(String subject) {
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

  public UUID publisherId() {
    return publisherId;
  }

  public ResourceKey key() {
    return key;
  }

  public DisplayName name() {
    return name;
  }

  public ChannelType type() {
    return type;
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
