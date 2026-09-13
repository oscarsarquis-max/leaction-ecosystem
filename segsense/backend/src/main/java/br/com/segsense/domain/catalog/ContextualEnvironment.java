package br.com.segsense.domain.catalog;

import java.time.Instant;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

public final class ContextualEnvironment {

  private final UUID id;
  private final UUID publisherId;
  private final UUID channelId;
  private final ResourceKey key;
  private DisplayName name;
  private final EnvironmentType type;
  private final CanonicalUrl canonicalUrl;
  private LifecycleStatus status;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;

  private ContextualEnvironment(
      UUID id,
      UUID publisherId,
      UUID channelId,
      ResourceKey key,
      DisplayName name,
      EnvironmentType type,
      CanonicalUrl canonicalUrl,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    this.id = Objects.requireNonNull(id, "id");
    this.publisherId = Objects.requireNonNull(publisherId, "publisherId");
    this.channelId = Objects.requireNonNull(channelId, "channelId");
    this.key = Objects.requireNonNull(key, "key");
    this.name = Objects.requireNonNull(name, "name");
    this.type = Objects.requireNonNull(type, "type");
    this.canonicalUrl = canonicalUrl;
    this.status = Objects.requireNonNull(status, "status");
    this.version = version;
    this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
    this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt");
    this.createdBy = requireSubject(createdBy);
    this.updatedBy = requireSubject(updatedBy);
  }

  public static ContextualEnvironment create(
      UUID id,
      Publisher publisher,
      Channel channel,
      ResourceKey key,
      DisplayName name,
      EnvironmentType type,
      CanonicalUrl canonicalUrl,
      Instant now,
      String actorSubject) {
    Objects.requireNonNull(publisher, "publisher");
    Objects.requireNonNull(channel, "channel");
    if (!channel.publisherId().equals(publisher.id())) {
      throw new ResourceNotFoundException();
    }
    String subject = requireSubject(actorSubject);
    Instant timestamp = Objects.requireNonNull(now, "now");
    return new ContextualEnvironment(
        id,
        publisher.id(),
        channel.id(),
        key,
        name,
        type,
        canonicalUrl,
        LifecycleStatus.DRAFT,
        0L,
        timestamp,
        timestamp,
        subject,
        subject);
  }

  public static ContextualEnvironment restore(
      UUID id,
      UUID publisherId,
      UUID channelId,
      ResourceKey key,
      DisplayName name,
      EnvironmentType type,
      CanonicalUrl canonicalUrl,
      LifecycleStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy) {
    return new ContextualEnvironment(
        id,
        publisherId,
        channelId,
        key,
        name,
        type,
        canonicalUrl,
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

  public void transitionTo(
      LifecycleStatus target, Publisher publisher, Channel channel, Instant now, String actorSubject) {
    Objects.requireNonNull(target, "target");
    Objects.requireNonNull(publisher, "publisher");
    Objects.requireNonNull(channel, "channel");
    if (!publisher.id().equals(publisherId) || !channel.id().equals(channelId)) {
      throw new ResourceNotFoundException();
    }
    if (!channel.publisherId().equals(publisher.id())) {
      throw new ResourceNotFoundException();
    }
    if (!status.canTransitionTo(target)) {
      throw new InvalidStateTransitionException();
    }
    if (target == LifecycleStatus.ACTIVE
        && (publisher.status() != LifecycleStatus.ACTIVE
            || channel.status() != LifecycleStatus.ACTIVE)) {
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

  public boolean effectivelyAvailable(Publisher publisher, Channel channel) {
    Objects.requireNonNull(publisher, "publisher");
    Objects.requireNonNull(channel, "channel");
    return status == LifecycleStatus.ACTIVE
        && channel.effectivelyAvailable(publisher);
  }

  public Optional<CanonicalUrl> canonicalUrl() {
    return Optional.ofNullable(canonicalUrl);
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

  public UUID channelId() {
    return channelId;
  }

  public ResourceKey key() {
    return key;
  }

  public DisplayName name() {
    return name;
  }

  public EnvironmentType type() {
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
