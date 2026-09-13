package br.com.segsense.infrastructure.catalog;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.application.catalog.EnvironmentRepository;
import br.com.segsense.domain.catalog.CanonicalUrl;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.EnvironmentType;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.ResourceKey;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class JpaEnvironmentRepository implements EnvironmentRepository {

  private final EnvironmentSpringRepository spring;

  public JpaEnvironmentRepository(EnvironmentSpringRepository spring) {
    this.spring = spring;
  }

  @Override
  public ContextualEnvironment save(ContextualEnvironment environment) {
    EnvironmentJpaEntity entity =
        spring.findById(environment.id()).orElseGet(EnvironmentJpaEntity::new);
    boolean creating = entity.getId() == null;
    entity.setId(environment.id());
    entity.setPublisherId(environment.publisherId());
    entity.setChannelId(environment.channelId());
    entity.setKey(environment.key().value());
    entity.setName(environment.name().value());
    entity.setType(environment.type().name());
    entity.setCanonicalUrl(environment.canonicalUrl().map(CanonicalUrl::value).orElse(null));
    entity.setStatus(environment.status().name());
    entity.setUpdatedAt(environment.updatedAt());
    entity.setUpdatedBy(environment.updatedBy());
    if (creating) {
      entity.setCreatedAt(environment.createdAt());
      entity.setCreatedBy(environment.createdBy());
    }
    try {
      return toDomain(spring.saveAndFlush(entity));
    } catch (DataIntegrityViolationException ex) {
      throw new DuplicateResourceKeyException(
          "ENVIRONMENT_KEY_CONFLICT", "Já existe um ambiente com esta chave neste canal.");
    }
  }

  @Override
  public Optional<ContextualEnvironment> findByIdAndPublisherIdAndChannelId(
      UUID environmentId, UUID publisherId, UUID channelId) {
    return spring
        .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
        .map(JpaEnvironmentRepository::toDomain);
  }

  @Override
  public boolean existsByChannelIdAndKey(UUID channelId, ResourceKey key) {
    return spring.existsByChannelIdAndKey(channelId, key.value());
  }

  @Override
  public List<ContextualEnvironment> listAfter(
      UUID publisherId, UUID channelId, CatalogCursor after, int limit) {
    boolean hasCursor = after != null;
    Instant createdAt = hasCursor ? after.createdAt() : Instant.EPOCH;
    UUID id = hasCursor ? after.id() : new UUID(0, 0);
    return spring
        .listAfter(publisherId, channelId, hasCursor, createdAt, id, PageRequest.of(0, limit))
        .stream()
        .map(JpaEnvironmentRepository::toDomain)
        .toList();
  }

  static ContextualEnvironment toDomain(EnvironmentJpaEntity entity) {
    return ContextualEnvironment.restore(
        entity.getId(),
        entity.getPublisherId(),
        entity.getChannelId(),
        ResourceKey.restored(entity.getKey()),
        DisplayName.parse(entity.getName()),
        EnvironmentType.valueOf(entity.getType()),
        CanonicalUrl.parseOptional(entity.getCanonicalUrl()).orElse(null),
        LifecycleStatus.valueOf(entity.getStatus()),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy());
  }
}
